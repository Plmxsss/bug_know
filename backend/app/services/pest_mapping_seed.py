"""Idempotently seed model classes as unreviewed pest entity mappings."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import (
    EntityAliasRepository,
    ModelClassMappingRepository,
    PestEntityRepository,
)
from app.services.class_catalog import ModelClass, normalize_alias


@dataclass(frozen=True, slots=True)
class SeedSummary:
    """Counts that make a seed run easy to verify."""

    classes_seen: int
    entities_created: int
    aliases_created: int
    mappings_created: int
    mappings_updated: int


class PestMappingSeedService:
    """Create traceable skeletons without claiming taxonomy or knowledge review."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._entities = PestEntityRepository(session)
        self._aliases = EntityAliasRepository(session)
        self._mappings = ModelClassMappingRepository(session)

    async def seed(
        self,
        *,
        model_version_id: int,
        catalog: tuple[ModelClass, ...],
    ) -> SeedSummary:
        """Upsert one complete class catalog inside the caller's transaction."""

        entities_created = 0
        aliases_created = 0
        mappings_created = 0
        mappings_updated = 0

        for model_class in catalog:
            entity = await self._entities.get_by_common_name(
                model_class.raw_class_name
            )
            if entity is None:
                entity = await self._entities.create_skeleton(
                    entity_code=f"ip102-class-{model_class.class_id:03d}",
                    common_name=model_class.raw_class_name,
                )
                entities_created += 1

            normalized = normalize_alias(model_class.raw_class_name)
            alias = await self._aliases.get_by_normalized_alias(
                normalized_alias=normalized,
                language="zh-CN",
            )
            if alias is None:
                await self._aliases.create(
                    entity_id=entity.id,
                    alias=model_class.raw_class_name,
                    normalized_alias=normalized,
                    language="zh-CN",
                    alias_type="model_label",
                )
                aliases_created += 1
            elif alias.entity_id != entity.id:
                raise ValueError(
                    f"Alias {model_class.raw_class_name!r} belongs to another entity."
                )

            mapping = await self._mappings.get_by_model_and_class(
                model_version_id=model_version_id,
                class_id=model_class.class_id,
            )
            if mapping is None:
                await self._mappings.create(
                    model_version_id=model_version_id,
                    class_id=model_class.class_id,
                    raw_class_name=model_class.raw_class_name,
                    pest_entity_id=entity.id,
                )
                mappings_created += 1
            elif (
                mapping.raw_class_name != model_class.raw_class_name
                or mapping.pest_entity_id != entity.id
            ):
                if mapping.mapping_status == "verified":
                    raise ValueError(
                        f"Verified class {model_class.class_id} conflicts with "
                        "the imported catalog."
                    )
                mapping.raw_class_name = model_class.raw_class_name
                mapping.pest_entity_id = entity.id
                mapping.mapping_status = "needs_review"
                mappings_updated += 1

        await self._session.flush()
        return SeedSummary(
            classes_seen=len(catalog),
            entities_created=entities_created,
            aliases_created=aliases_created,
            mappings_created=mappings_created,
            mappings_updated=mappings_updated,
        )
