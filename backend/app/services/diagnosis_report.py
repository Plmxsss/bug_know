"""Orchestrate detection facts, RAG retrieval, LLM generation, and persistence."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.llm import LLMProvider, LLMProviderError, LLMUsage
from app.models import DiagnosisReport
from app.rag.embeddings import TextEmbedder
from app.rag.vector_database import VectorDatabaseGateway
from app.repositories import (
    DetectionObjectRepository,
    DetectionTaskRepository,
    DiagnosisReportRepository,
    PestEntityRepository,
)
from app.schemas.diagnosis import DiagnosisReportContent
from app.services.knowledge_search import KnowledgeSearchService
from app.services.report_generation import (
    PROMPT_VERSION,
    DetectedEntityContext,
    GeneratedReport,
    ReportGenerator,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StoredDiagnosisReport:
    """Plain, validated values returned by both create and read operations."""

    id: int
    task_id: int
    status: Literal["completed"]
    llm_provider: str
    llm_model: str
    prompt_version: str
    report: DiagnosisReportContent
    usage: LLMUsage
    created_at: datetime
    completed_at: datetime


class DiagnosisReportService:
    """Generate at most one current report per completed detection task."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        vector_database: VectorDatabaseGateway,
        embedder: TextEmbedder | None,
        llm_provider: LLMProvider | None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._vector_database = vector_database
        self._embedder = embedder
        self._llm_provider = llm_provider
        self._tasks = DetectionTaskRepository(session)
        self._objects = DetectionObjectRepository(session)
        self._entities = PestEntityRepository(session)
        self._reports = DiagnosisReportRepository(session)

    async def generate(self, task_id: int) -> StoredDiagnosisReport:
        """Return an existing completed report or safely generate it once."""

        existing = await self._reports.get_by_task_id(task_id)
        if existing is not None:
            if existing.status == "completed":
                return self._stored(existing)
            if existing.status == "processing":
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    code="DIAGNOSIS_ALREADY_PROCESSING",
                    message=f"Diagnosis for task {task_id} is already processing.",
                )

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
                message="Diagnosis requires a completed detection task.",
            )

        objects = await self._objects.list_by_task_id(task_id)
        if not objects:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="NO_DETECTED_PESTS",
                message="The completed task contains no detected pests.",
            )
        untrusted_names = sorted(
            {
                detected.raw_class_name
                for detected in objects
                if detected.normalized_entity_id is None
            }
        )
        if untrusted_names:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="DETECTION_HAS_UNVERIFIED_ENTITIES",
                message="Every detected class must have a verified entity mapping.",
                details={"raw_class_names": untrusted_names},
            )

        entity_ids = sorted(
            {
                cast(int, detected.normalized_entity_id)
                for detected in objects
            }
        )
        entities = {
            entity.id: entity
            for entity in await self._entities.get_by_ids(entity_ids)
        }
        if set(entities) != set(entity_ids):
            raise RuntimeError("A normalized detection references a missing entity.")
        not_reviewed = [
            {
                "entity_id": entity.id,
                "name": entity.common_name,
                "knowledge_status": entity.knowledge_status,
            }
            for entity in entities.values()
            if entity.knowledge_status != "reviewed"
        ]
        if not_reviewed:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="KNOWLEDGE_NOT_REVIEWED",
                message="Diagnosis requires reviewed knowledge for every entity.",
                details={"entities": not_reviewed},
            )
        if self._embedder is None:
            raise AppError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="EMBEDDING_MODEL_DISABLED",
                message="The embedding model is not enabled on this API instance.",
            )
        if self._llm_provider is None:
            raise AppError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="LLM_PROVIDER_DISABLED",
                message="The language-model provider is not enabled.",
            )

        contexts: list[DetectedEntityContext] = []
        for entity_id in entity_ids:
            entity_objects = [
                detected
                for detected in objects
                if detected.normalized_entity_id == entity_id
            ]
            entity = entities[entity_id]
            retrieval = await KnowledgeSearchService(
                session=self._session,
                settings=self._settings,
                embedder=self._embedder,
                vector_database=self._vector_database,
            ).search(
                entity_id=entity_id,
                query=(
                    f"{entity.common_name}的基本介绍、典型特征、寄主植物、主要危害、"
                    "发生条件、预防措施和综合防治建议"
                ),
                top_k=self._settings.rag_top_k,
            )
            if not retrieval.hits:
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    code="KNOWLEDGE_RETRIEVAL_EMPTY",
                    message=(
                        f"No reviewed knowledge chunks were retrieved for "
                        f"entity {entity_id}."
                    ),
                )
            contexts.append(
                DetectedEntityContext(
                    entity_id=entity_id,
                    name=entity.common_name,
                    confidence=max(item.confidence for item in entity_objects),
                    count=len(entity_objects),
                    knowledge_status=entity.knowledge_status,
                    hits=retrieval.hits,
                )
            )

        await self._session.commit()
        claimed, should_generate = await self._claim(task_id)
        if not should_generate:
            return self._stored(claimed)

        try:
            generated = await ReportGenerator(self._llm_provider).generate(
                tuple(contexts)
            )
            completed = await self._complete(claimed.id, generated)
            return self._stored(completed)
        except LLMProviderError as exc:
            await self._session.rollback()
            await self._record_failure(claimed.id, exc)
            raise AppError(
                status_code=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                    if exc.retryable
                    else status.HTTP_502_BAD_GATEWAY
                ),
                code=exc.code,
                message=str(exc),
            ) from exc
        except Exception as exc:
            await self._session.rollback()
            await self._record_failure(claimed.id, exc)
            raise

    async def get_completed(self, task_id: int) -> StoredDiagnosisReport:
        """Return a completed persisted report or a clear API error."""

        report = await self._reports.get_by_task_id(task_id)
        if report is None or report.status != "completed":
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="DIAGNOSIS_REPORT_NOT_FOUND",
                message=f"No completed diagnosis report exists for task {task_id}.",
            )
        return self._stored(report)

    async def _claim(
        self,
        task_id: int,
    ) -> tuple[DiagnosisReport, bool]:
        """Serialize concurrent callers and reserve the unique task report."""

        async with self._session.begin():
            task = await self._tasks.get_by_id_for_update(task_id)
            if task is None or task.status != "completed":
                raise RuntimeError("Detection task changed before diagnosis claim.")
            report = await self._reports.get_by_task_id_for_update(task_id)
            if report is None:
                report = await self._reports.create_processing(
                    task_id=task_id,
                    prompt_version=PROMPT_VERSION,
                )
                return report, True
            if report.status == "completed":
                return report, False
            if report.status == "processing":
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    code="DIAGNOSIS_ALREADY_PROCESSING",
                    message=f"Diagnosis for task {task_id} is already processing.",
                )
            report.status = "processing"
            report.prompt_version = PROMPT_VERSION
            report.llm_provider = None
            report.llm_model = None
            report.report_json = None
            report.prompt_tokens = None
            report.completion_tokens = None
            report.total_tokens = None
            report.error_message = None
            report.completed_at = None
            await self._session.flush()
            return report, True

    async def _complete(
        self,
        report_id: int,
        generated: GeneratedReport,
    ) -> DiagnosisReport:
        """Persist only a fully validated generated report."""

        async with self._session.begin():
            report = await self._session.get(
                DiagnosisReport,
                report_id,
                with_for_update=True,
            )
            if report is None or report.status != "processing":
                raise RuntimeError("Diagnosis report state changed unexpectedly.")
            report.status = "completed"
            report.llm_provider = generated.provider
            report.llm_model = generated.model
            report.prompt_version = generated.prompt_version
            report.report_json = generated.content.model_dump(mode="json")
            report.prompt_tokens = generated.usage.prompt_tokens
            report.completion_tokens = generated.usage.completion_tokens
            report.total_tokens = generated.usage.total_tokens
            report.error_message = None
            report.completed_at = datetime.now(UTC)
            await self._session.flush()
            await self._session.refresh(report)
            return report

    async def _record_failure(self, report_id: int, exc: Exception) -> None:
        """Best-effort report failure recording without exposing secrets."""

        try:
            async with self._session.begin():
                report = await self._session.get(
                    DiagnosisReport,
                    report_id,
                    with_for_update=True,
                )
                if report is not None and report.status == "processing":
                    report.status = "failed"
                    report.error_message = f"{type(exc).__name__}: {exc}"[:2000]
                    report.completed_at = datetime.now(UTC)
                    await self._session.flush()
        except Exception:
            logger.exception(
                "Could not mark diagnosis report %s as failed",
                report_id,
            )

    @staticmethod
    def _stored(report: DiagnosisReport) -> StoredDiagnosisReport:
        """Validate database JSON before exposing a completed report."""

        if (
            report.status != "completed"
            or report.report_json is None
            or report.llm_provider is None
            or report.llm_model is None
            or report.completed_at is None
        ):
            raise RuntimeError("Diagnosis report is not complete.")
        return StoredDiagnosisReport(
            id=report.id,
            task_id=report.task_id,
            status="completed",
            llm_provider=report.llm_provider,
            llm_model=report.llm_model,
            prompt_version=report.prompt_version,
            report=DiagnosisReportContent.model_validate(report.report_json),
            usage=LLMUsage(
                prompt_tokens=report.prompt_tokens,
                completion_tokens=report.completion_tokens,
                total_tokens=report.total_tokens,
            ),
            created_at=report.created_at,
            completed_at=report.completed_at,
        )
