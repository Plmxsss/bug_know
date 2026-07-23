"""Tests for safe and repeatable pest mapping imports."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EntityAlias, ModelClassMapping, PestEntity
from app.services.class_catalog import ModelClass
from app.services.pest_mapping_seed import PestMappingSeedService


def _service() -> PestMappingSeedService:
    session = AsyncMock(spec=AsyncSession)
    return PestMappingSeedService(session)


async def test_seed_leaves_matching_existing_rows_unchanged() -> None:
    """A second identical import should create and update nothing."""

    service = _service()
    entity = PestEntity(id=8, common_name="褐飞虱")
    alias = EntityAlias(id=9, entity_id=8)
    mapping = ModelClassMapping(
        id=10,
        model_version_id=1,
        class_id=7,
        raw_class_name="褐飞虱",
        pest_entity_id=8,
        mapping_status="needs_review",
    )
    service._entities.get_by_common_name = AsyncMock(return_value=entity)
    service._aliases.get_by_normalized_alias = AsyncMock(return_value=alias)
    service._mappings.get_by_model_and_class = AsyncMock(return_value=mapping)

    summary = await service.seed(
        model_version_id=1,
        catalog=(ModelClass(class_id=7, raw_class_name="褐飞虱"),),
    )

    assert summary.entities_created == 0
    assert summary.aliases_created == 0
    assert summary.mappings_created == 0
    assert summary.mappings_updated == 0


async def test_seed_refuses_to_overwrite_verified_conflict() -> None:
    """Changed training labels must not silently rewrite human-reviewed data."""

    service = _service()
    entity = PestEntity(id=8, common_name="新标签")
    alias = EntityAlias(id=9, entity_id=8)
    mapping = ModelClassMapping(
        id=10,
        model_version_id=1,
        class_id=7,
        raw_class_name="旧标签",
        pest_entity_id=6,
        mapping_status="verified",
    )
    service._entities.get_by_common_name = AsyncMock(return_value=entity)
    service._aliases.get_by_normalized_alias = AsyncMock(return_value=alias)
    service._mappings.get_by_model_and_class = AsyncMock(return_value=mapping)

    with pytest.raises(ValueError, match="Verified class 7 conflicts"):
        await service.seed(
            model_version_id=1,
            catalog=(ModelClass(class_id=7, raw_class_name="新标签"),),
        )
