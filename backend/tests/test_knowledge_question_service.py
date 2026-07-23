"""Tests for bounded Agent retrieval followed by structured generation."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.llm import LLMUsage, StructuredLLMResult
from app.models import DetectionObject, DetectionTask, PestEntity
from app.schemas.knowledge_question import KnowledgeQuestionSynthesis
from app.services.knowledge_question import KnowledgeQuestionService
from app.services.knowledge_search import (
    KnowledgeSearchResult,
    RetrievedKnowledge,
)


def _hit() -> RetrievedKnowledge:
    return RetrievedKnowledge(
        point_id="trusted-point",
        score=0.91,
        document_id=2,
        heading="为害特征",
        locator="heading:为害特征",
        content="稻纵卷叶螟幼虫卷叶并取食叶肉。",
        title="水稻害虫资料",
        source_organization="农业技术机构",
        source_url="https://example.org/rice",
        publication_date=date(2026, 5, 26),
        region="测试地区",
    )


class FakePlanner:
    """Call the server-owned search closure exactly once."""

    async def plan(self, *, question, search):
        assert question == "它怎样危害水稻？"
        tool_json = await search("稻纵卷叶螟 危害")
        assert "trusted-point" in tool_json
        return SimpleNamespace(queries=("稻纵卷叶螟 危害",))


class FakeProvider:
    """Return configured structured output without a model request."""

    def __init__(self, citation_id: str = "trusted-point") -> None:
        self._citation_id = citation_id

    async def generate_structured(self, *, messages, response_model):
        assert "trusted-point" in messages[1].content
        return StructuredLLMResult(
            value=KnowledgeQuestionSynthesis(
                answer="幼虫卷叶并取食水稻叶肉。",
                uncertainty="具体发生程度需结合当地田间调查。",
                citation_point_ids=[self._citation_id],
            ),
            provider="mock",
            model="mock-model",
            usage=LLMUsage(10, 10, 20),
        )

    async def close(self) -> None:
        return None


def _service(provider: FakeProvider) -> KnowledgeQuestionService:
    session = AsyncMock(spec=AsyncSession)
    service = KnowledgeQuestionService(
        session=session,
        settings=Settings(_env_file=None),
        vector_database=Mock(),
        embedder=Mock(),
        llm_provider=provider,
        query_planner=FakePlanner(),
    )
    service._tasks.get_by_id = AsyncMock(
        return_value=DetectionTask(id=7, status="completed")
    )
    service._objects.list_by_task_id = AsyncMock(
        return_value=[
            DetectionObject(
                id=1,
                task_id=7,
                class_id=0,
                raw_class_name="稻纵卷叶螟",
                normalized_entity_id=1,
                confidence=0.91,
                bbox_x1=1,
                bbox_y1=2,
                bbox_x2=20,
                bbox_y2=30,
            )
        ]
    )
    service._entities.get_by_ids = AsyncMock(
        return_value=[
            PestEntity(
                id=1,
                entity_code="ip102-class-000",
                common_name="稻纵卷叶螟",
                knowledge_status="reviewed",
            )
        ]
    )
    return service


async def test_question_uses_agent_tool_hits_and_rebuilds_reference() -> None:
    """A valid citation should be reconstructed from trusted retrieval metadata."""

    search_result = KnowledgeSearchResult(
        entity_id=1,
        common_name="稻纵卷叶螟",
        knowledge_status="reviewed",
        hits=(_hit(),),
    )
    with patch(
        "app.services.knowledge_question.KnowledgeSearchService.search",
        new=AsyncMock(return_value=search_result),
    ):
        result = await _service(FakeProvider()).answer(
            task_id=7,
            question="它怎样危害水稻？",
        )

    assert result.planned_queries == ("稻纵卷叶螟 危害",)
    assert result.answer == "幼虫卷叶并取食水稻叶肉。"
    assert result.references[0].document_id == 2
    assert result.references[0].source_organization == "农业技术机构"


async def test_question_rejects_citation_outside_agent_retrieval() -> None:
    """A plausible but unobserved point ID must never reach the API response."""

    search_result = KnowledgeSearchResult(
        entity_id=1,
        common_name="稻纵卷叶螟",
        knowledge_status="reviewed",
        hits=(_hit(),),
    )
    with patch(
        "app.services.knowledge_question.KnowledgeSearchService.search",
        new=AsyncMock(return_value=search_result),
    ):
        with pytest.raises(AppError) as exc_info:
            await _service(FakeProvider("invented-point")).answer(
                task_id=7,
                question="它怎样危害水稻？",
            )

    assert exc_info.value.code == "LLM_INVALID_CITATIONS"
