"""Tests for the trust boundary between model labels and pest entities."""

from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ModelClassMapping, PestEntity
from app.services import EntityNormalizer


def _normalizer() -> EntityNormalizer:
    return EntityNormalizer(AsyncMock(spec=AsyncSession))


async def test_missing_mapping_is_explicitly_unmapped() -> None:
    """No row must produce no entity ID rather than a name-based guess."""

    normalizer = _normalizer()
    normalizer._repository.get_with_entity = AsyncMock(return_value=None)

    result = await normalizer.normalize_one(
        model_version_id=1,
        class_id=5,
        raw_class_name="稻瘿蚊",
    )

    assert result.status == "unmapped"
    assert result.entity_id is None


async def test_unreviewed_mapping_cannot_become_normalized() -> None:
    """A seeded mapping remains outside the trusted RAG path."""

    normalizer = _normalizer()
    mapping = ModelClassMapping(
        model_version_id=1,
        class_id=5,
        raw_class_name="稻瘿蚊",
        pest_entity_id=20,
        mapping_status="needs_review",
    )
    entity = PestEntity(
        id=20,
        entity_code="ip102-class-005",
        common_name="稻瘿蚊",
        knowledge_status="missing",
    )
    normalizer._repository.get_with_entity = AsyncMock(
        return_value=(mapping, entity)
    )

    result = await normalizer.normalize_one(
        model_version_id=1,
        class_id=5,
        raw_class_name="稻瘿蚊",
    )

    assert result.status == "needs_review"
    assert result.entity_id is None


async def test_verified_mapping_returns_entity_and_knowledge_state() -> None:
    """Verification permits identity mapping but does not invent knowledge."""

    normalizer = _normalizer()
    mapping = ModelClassMapping(
        model_version_id=1,
        class_id=5,
        raw_class_name="稻瘿蚊",
        pest_entity_id=20,
        mapping_status="verified",
    )
    entity = PestEntity(
        id=20,
        entity_code="ip102-class-005",
        common_name="稻瘿蚊",
        knowledge_status="missing",
    )
    normalizer._repository.get_with_entity = AsyncMock(
        return_value=(mapping, entity)
    )

    result = await normalizer.normalize_one(
        model_version_id=1,
        class_id=5,
        raw_class_name="稻瘿蚊",
    )

    assert result.status == "verified"
    assert result.entity_id == 20
    assert result.knowledge_status == "missing"
