"""Answer task-scoped follow-up questions through a bounded Agent tool."""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, cast

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.llm import ChatMessage, LLMProvider, LLMProviderError
from app.rag.embeddings import TextEmbedder
from app.rag.vector_database import VectorDatabaseGateway
from app.repositories import (
    DetectionObjectRepository,
    DetectionTaskRepository,
    PestEntityRepository,
)
from app.schemas.diagnosis import DiagnosisReference
from app.schemas.knowledge_question import KnowledgeQuestionSynthesis
from app.services.knowledge_search import (
    KnowledgeSearchService,
    RetrievedKnowledge,
)
from app.services.report_generation import reject_universal_pesticide_dosage


class QueryPlan(Protocol):
    """Framework-independent result returned by the Agent adapter."""

    queries: tuple[str, ...]


class QueryPlanner(Protocol):
    """Only Agent behavior required by the knowledge-question service."""

    async def plan(
        self,
        *,
        question: str,
        search: Callable[[str], Awaitable[str]],
    ) -> QueryPlan:
        """Call the task-scoped retrieval tool at least once."""


@dataclass(frozen=True, slots=True)
class KnowledgeQuestionResult:
    """Validated answer values returned to the API layer."""

    task_id: int
    question: str
    planned_queries: tuple[str, ...]
    answer: str
    uncertainty: str
    references: tuple[DiagnosisReference, ...]


class KnowledgeQuestionService:
    """Keep Agent planning, retrieval, and answer generation separately gated."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        vector_database: VectorDatabaseGateway,
        embedder: TextEmbedder,
        llm_provider: LLMProvider,
        query_planner: QueryPlanner,
    ) -> None:
        self._session = session
        self._settings = settings
        self._vector_database = vector_database
        self._embedder = embedder
        self._llm_provider = llm_provider
        self._query_planner = query_planner
        self._tasks = DetectionTaskRepository(session)
        self._objects = DetectionObjectRepository(session)
        self._entities = PestEntityRepository(session)

    async def answer(
        self,
        *,
        task_id: int,
        question: str,
    ) -> KnowledgeQuestionResult:
        """Plan retrieval, search allowed entities, and validate final citations."""

        entity_ids = await self._reviewed_entity_ids(task_id)
        hits_by_id: dict[str, RetrievedKnowledge] = {}
        search_service = KnowledgeSearchService(
            session=self._session,
            settings=self._settings,
            embedder=self._embedder,
            vector_database=self._vector_database,
        )

        async def search_allowed_entities(query: str) -> str:
            tool_hits: list[dict[str, object]] = []
            for entity_id in entity_ids:
                result = await search_service.search(
                    entity_id=entity_id,
                    query=query,
                    top_k=self._settings.rag_top_k,
                )
                for hit in result.hits:
                    hits_by_id.setdefault(hit.point_id, hit)
                    tool_hits.append(self._agent_hit(hit))
            return json.dumps({"results": tool_hits}, ensure_ascii=False)

        try:
            plan = await self._query_planner.plan(
                question=question,
                search=search_allowed_entities,
            )
            if not hits_by_id:
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    code="KNOWLEDGE_RETRIEVAL_EMPTY",
                    message="The Agent tool found no reviewed knowledge evidence.",
                )
            synthesis_result = await self._llm_provider.generate_structured(
                messages=self._answer_messages(
                    question=question,
                    hits=tuple(hits_by_id.values()),
                ),
                response_model=KnowledgeQuestionSynthesis,
            )
        except LLMProviderError as exc:
            raise AppError(
                status_code=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                    if exc.retryable
                    else status.HTTP_502_BAD_GATEWAY
                ),
                code=exc.code,
                message=str(exc),
            ) from exc

        synthesis = synthesis_result.value
        selected_ids = synthesis.citation_point_ids
        if (
            len(selected_ids) != len(set(selected_ids))
            or not set(selected_ids).issubset(hits_by_id)
        ):
            raise AppError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code="LLM_INVALID_CITATIONS",
                message="The generated answer cited evidence outside the Agent retrieval.",
            )
        try:
            reject_universal_pesticide_dosage(
                synthesis.model_dump_json(exclude={"citation_point_ids"})
            )
        except LLMProviderError as exc:
            raise AppError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code=exc.code,
                message=str(exc),
            ) from exc
        references = tuple(
            self._reference(hits_by_id[point_id])
            for point_id in selected_ids
        )
        return KnowledgeQuestionResult(
            task_id=task_id,
            question=question,
            planned_queries=plan.queries,
            answer=synthesis.answer,
            uncertainty=synthesis.uncertainty,
            references=references,
        )

    async def _reviewed_entity_ids(self, task_id: int) -> tuple[int, ...]:
        """Resolve server-owned entity scope and reject unreviewed detections."""

        task = await self._tasks.get_by_id(task_id)
        if task is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="DETECTION_TASK_NOT_FOUND",
                message=f"Detection task {task_id} does not exist.",
            )
        if task.status != "completed":
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="DETECTION_TASK_NOT_COMPLETED",
                message="Knowledge questions require a completed detection task.",
            )
        objects = await self._objects.list_by_task_id(task_id)
        if not objects:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="NO_DETECTED_PESTS",
                message="The completed task contains no detected pests.",
            )
        if any(item.normalized_entity_id is None for item in objects):
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="DETECTION_HAS_UNVERIFIED_ENTITIES",
                message="Every detected class must have a verified entity mapping.",
            )
        entity_ids = tuple(
            sorted(
                {
                    cast(int, item.normalized_entity_id)
                    for item in objects
                }
            )
        )
        entities = await self._entities.get_by_ids(entity_ids)
        if len(entities) != len(entity_ids) or any(
            entity.knowledge_status != "reviewed" for entity in entities
        ):
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="KNOWLEDGE_NOT_REVIEWED",
                message="Questions require reviewed knowledge for every entity.",
            )
        return entity_ids

    @staticmethod
    def _agent_hit(hit: RetrievedKnowledge) -> dict[str, object]:
        """Expose only evidence text and citation metadata to the Agent tool."""

        return {
            "point_id": hit.point_id,
            "content": hit.content,
            "title": hit.title,
            "source_organization": hit.source_organization,
            "locator": hit.locator,
            "region": hit.region,
        }

    @staticmethod
    def _answer_messages(
        *,
        question: str,
        hits: tuple[RetrievedKnowledge, ...],
    ) -> tuple[ChatMessage, ...]:
        """Build the separate structured synthesis request."""

        evidence = [
            KnowledgeQuestionService._agent_hit(hit)
            for hit in hits
        ]
        return (
            ChatMessage(
                role="system",
                content=(
                    "只能依据 evidence 回答农业问题。资料未覆盖的内容必须明确"
                    "说明不足，不得使用模型自身知识，不得给出跨地区通用农药剂量。"
                    "citation_point_ids 只能选择 evidence 中实际支持答案的编号。"
                    "只输出符合 JSON Schema 的对象。"
                ),
            ),
            ChatMessage(
                role="user",
                content=json.dumps(
                    {"question": question, "evidence": evidence},
                    ensure_ascii=False,
                ),
            ),
        )

    @staticmethod
    def _reference(hit: RetrievedKnowledge) -> DiagnosisReference:
        """Rebuild citations from trusted MySQL metadata."""

        return DiagnosisReference(
            point_id=hit.point_id,
            document_id=hit.document_id,
            title=hit.title,
            source_organization=hit.source_organization,
            source_url=hit.source_url,
            publication_date=(
                hit.publication_date.isoformat()
                if hit.publication_date
                else None
            ),
            region=hit.region,
            locator=hit.locator,
        )
