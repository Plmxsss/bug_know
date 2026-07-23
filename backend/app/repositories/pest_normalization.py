"""Database operations for pest entities, aliases, and model mappings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EntityAlias, ModelClassMapping, PestEntity


class PestEntityRepository:
    """Read and create normalized pest identities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_common_name(self, common_name: str) -> PestEntity | None:
        """Find one entity by its displayed common name."""

        result = await self._session.execute(
            select(PestEntity).where(PestEntity.common_name == common_name)
        )
        return result.scalar_one_or_none()

    async def get_by_code_for_update(self, entity_code: str) -> PestEntity | None:
        """Lock one entity while recording a knowledge review decision."""

        result = await self._session.execute(
            select(PestEntity)
            .where(PestEntity.entity_code == entity_code)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_skeleton(
        self,
        *,
        entity_code: str,
        common_name: str,
    ) -> PestEntity:
        """Create an entity that intentionally has no reviewed knowledge yet."""

        entity = PestEntity(
            entity_code=entity_code,
            common_name=common_name,
            scientific_name=None,
            description=None,
            knowledge_status="missing",
            knowledge_reviewed_at=None,
            knowledge_reviewed_by=None,
            knowledge_review_note=None,
        )
        self._session.add(entity)
        await self._session.flush()
        return entity


class EntityAliasRepository:
    """Read and create normalized aliases."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_normalized_alias(
        self,
        *,
        normalized_alias: str,
        language: str,
    ) -> EntityAlias | None:
        """Find one alias exactly as the database uniqueness rule sees it."""

        result = await self._session.execute(
            select(EntityAlias).where(
                EntityAlias.normalized_alias == normalized_alias,
                EntityAlias.language == language,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        entity_id: int,
        alias: str,
        normalized_alias: str,
        language: str,
        alias_type: str,
    ) -> EntityAlias:
        """Insert one alias and flush its generated primary key."""

        entity_alias = EntityAlias(
            entity_id=entity_id,
            alias=alias,
            normalized_alias=normalized_alias,
            language=language,
            alias_type=alias_type,
        )
        self._session.add(entity_alias)
        await self._session.flush()
        return entity_alias


class ModelClassMappingRepository:
    """Read and create links from model output IDs to pest entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_model_and_class(
        self,
        *,
        model_version_id: int,
        class_id: int,
    ) -> ModelClassMapping | None:
        """Find one class mapping for an exact model artifact."""

        result = await self._session.execute(
            select(ModelClassMapping).where(
                ModelClassMapping.model_version_id == model_version_id,
                ModelClassMapping.class_id == class_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_with_entity(
        self,
        *,
        model_version_id: int,
        class_id: int,
    ) -> tuple[ModelClassMapping, PestEntity | None] | None:
        """Load one mapping and its optional normalized entity."""

        statement = (
            select(ModelClassMapping, PestEntity)
            .outerjoin(
                PestEntity,
                ModelClassMapping.pest_entity_id == PestEntity.id,
            )
            .where(
                ModelClassMapping.model_version_id == model_version_id,
                ModelClassMapping.class_id == class_id,
            )
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    async def get_with_entity_for_update(
        self,
        *,
        model_version_id: int,
        class_id: int,
    ) -> tuple[ModelClassMapping, PestEntity | None] | None:
        """Lock one model-scoped mapping while recording a review decision."""

        statement = (
            select(ModelClassMapping, PestEntity)
            .outerjoin(
                PestEntity,
                ModelClassMapping.pest_entity_id == PestEntity.id,
            )
            .where(
                ModelClassMapping.model_version_id == model_version_id,
                ModelClassMapping.class_id == class_id,
            )
            .with_for_update()
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    async def create(
        self,
        *,
        model_version_id: int,
        class_id: int,
        raw_class_name: str,
        pest_entity_id: int,
    ) -> ModelClassMapping:
        """Create a link that remains untrusted until human review."""

        mapping = ModelClassMapping(
            model_version_id=model_version_id,
            class_id=class_id,
            raw_class_name=raw_class_name,
            pest_entity_id=pest_entity_id,
            mapping_status="needs_review",
            verified_at=None,
            verified_by=None,
            review_note=None,
        )
        self._session.add(mapping)
        await self._session.flush()
        return mapping
