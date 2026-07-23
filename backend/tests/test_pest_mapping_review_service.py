"""Tests for safe and auditable model-class mapping review."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ModelClassMapping, PestEntity
from app.services.pest_mapping_review import PestMappingReviewService


def _service() -> PestMappingReviewService:
    service = PestMappingReviewService(AsyncMock(spec=AsyncSession))
    service._model_versions = AsyncMock()
    service._mappings = AsyncMock()
    service._model_versions.get_by_name_and_version.return_value = SimpleNamespace(id=2)
    return service


def _mapping() -> tuple[ModelClassMapping, PestEntity]:
    return (
        ModelClassMapping(
            model_version_id=2,
            class_id=0,
            raw_class_name="稻纵卷叶螟",
            pest_entity_id=1,
            mapping_status="needs_review",
        ),
        PestEntity(
            id=1,
            entity_code="ip102-class-000",
            common_name="稻纵卷叶螟",
            knowledge_status="draft",
        ),
    )


async def test_verify_records_audit_only_after_exact_assertions_match() -> None:
    """A correct review should make the model-version mapping trusted."""

    service = _service()
    mapping, entity = _mapping()
    service._mappings.get_with_entity_for_update.return_value = (mapping, entity)

    result = await service.verify(
        model_name="ip102-yolo26n",
        model_version="1.0.0",
        class_id=0,
        expected_raw_class_name="稻纵卷叶螟",
        expected_entity_code="ip102-class-000",
        verified_by="project-owner",
        review_note="Compared training catalog and entity record.",
    )

    assert result.entity_id == 1
    assert mapping.mapping_status == "verified"
    assert mapping.verified_by == "project-owner"
    assert mapping.review_note == "Compared training catalog and entity record."
    assert mapping.verified_at is not None


async def test_verify_rejects_wrong_expected_label() -> None:
    """A copied class ID with the wrong label must not become trusted."""

    service = _service()
    mapping, entity = _mapping()
    service._mappings.get_with_entity_for_update.return_value = (mapping, entity)

    with pytest.raises(ValueError, match="raw class name"):
        await service.verify(
            model_name="ip102-yolo26n",
            model_version="1.0.0",
            class_id=0,
            expected_raw_class_name="错误类别",
            expected_entity_code="ip102-class-000",
            verified_by="project-owner",
            review_note="Should fail.",
        )

    assert mapping.mapping_status == "needs_review"
    assert mapping.verified_at is None
