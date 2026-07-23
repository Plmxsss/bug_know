"""Tests for evidence-gated pest knowledge review."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PestEntity
from app.repositories.knowledge_review import IndexedSourceEvidence
from app.services.knowledge_review import KnowledgeReviewService


def _service() -> tuple[KnowledgeReviewService, PestEntity]:
    service = KnowledgeReviewService(AsyncMock(spec=AsyncSession))
    service._entities = AsyncMock()
    service._evidence = AsyncMock()
    entity = PestEntity(
        id=1,
        entity_code="ip102-class-000",
        common_name="稻纵卷叶螟",
        knowledge_status="draft",
    )
    service._entities.get_by_code_for_update.return_value = entity
    return service, entity


async def test_review_requires_and_records_diverse_provenance() -> None:
    """Two independently published indexed sources can pass the gate."""

    service, entity = _service()
    service._evidence.list_indexed_source_evidence.return_value = [
        IndexedSourceEvidence(1, "陕西省农业农村厅", "https://example.org/1"),
        IndexedSourceEvidence(2, "武汉市农业技术推广中心", "https://example.org/2"),
    ]

    result = await service.review(
        entity_code="ip102-class-000",
        expected_common_name="稻纵卷叶螟",
        reviewed_by="project-maintainer",
        review_note="Compared both sources and regional safety boundaries.",
    )

    assert result.document_ids == (1, 2)
    assert entity.knowledge_status == "reviewed"
    assert entity.knowledge_reviewed_at is not None
    assert entity.knowledge_reviewed_by == "project-maintainer"


async def test_review_rejects_two_documents_from_one_organization() -> None:
    """Duplicating one publisher must not satisfy source independence."""

    service, entity = _service()
    service._evidence.list_indexed_source_evidence.return_value = [
        IndexedSourceEvidence(1, "Same publisher", "https://example.org/1"),
        IndexedSourceEvidence(2, "Same publisher", "https://example.org/2"),
    ]

    with pytest.raises(ValueError, match="two source organizations"):
        await service.review(
            entity_code="ip102-class-000",
            expected_common_name="稻纵卷叶螟",
            reviewed_by="project-maintainer",
            review_note="Should fail.",
        )

    assert entity.knowledge_status == "draft"
    assert entity.knowledge_reviewed_at is None
