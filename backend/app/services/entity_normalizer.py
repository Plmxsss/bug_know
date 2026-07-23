"""Resolve raw model detections to human-reviewed pest entities."""

from dataclasses import dataclass
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.predictors.types import Detection
from app.repositories import ModelClassMappingRepository

NormalizationStatus = Literal["unmapped", "needs_review", "verified"]
KnowledgeStatus = Literal["missing", "draft", "reviewed"]


@dataclass(frozen=True, slots=True)
class EntityNormalization:
    """Trust decision for one distinct model class in a prediction."""

    class_id: int
    raw_class_name: str
    status: NormalizationStatus
    entity_id: int | None
    entity_code: str | None
    common_name: str | None
    knowledge_status: KnowledgeStatus | None


class EntityNormalizer:
    """Enforce that only verified class mappings become normalized entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = ModelClassMappingRepository(session)

    async def normalize_many(
        self,
        *,
        model_version_id: int,
        detections: tuple[Detection, ...],
    ) -> dict[int, EntityNormalization]:
        """Resolve each distinct class ID once and return decisions by class."""

        class_names = {
            detection.class_id: detection.class_name for detection in detections
        }
        return {
            class_id: await self.normalize_one(
                model_version_id=model_version_id,
                class_id=class_id,
                raw_class_name=raw_class_name,
            )
            for class_id, raw_class_name in class_names.items()
        }

    async def normalize_one(
        self,
        *,
        model_version_id: int,
        class_id: int,
        raw_class_name: str,
    ) -> EntityNormalization:
        """Return an explicit non-trusted state instead of guessing an entity."""

        resolved = await self._repository.get_with_entity(
            model_version_id=model_version_id,
            class_id=class_id,
        )
        if resolved is None:
            return self._untrusted(class_id, raw_class_name, "unmapped")

        mapping, entity = resolved
        if (
            mapping.mapping_status != "verified"
            or mapping.raw_class_name != raw_class_name
            or entity is None
        ):
            return self._untrusted(class_id, raw_class_name, "needs_review")

        return EntityNormalization(
            class_id=class_id,
            raw_class_name=raw_class_name,
            status="verified",
            entity_id=entity.id,
            entity_code=entity.entity_code,
            common_name=entity.common_name,
            knowledge_status=cast(KnowledgeStatus, entity.knowledge_status),
        )

    @staticmethod
    def _untrusted(
        class_id: int,
        raw_class_name: str,
        status: Literal["unmapped", "needs_review"],
    ) -> EntityNormalization:
        """Build a result that cannot accidentally be used as a RAG filter."""

        return EntityNormalization(
            class_id=class_id,
            raw_class_name=raw_class_name,
            status=status,
            entity_id=None,
            entity_code=None,
            common_name=None,
            knowledge_status=None,
        )
