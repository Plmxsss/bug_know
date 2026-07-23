"""Record an explicit, auditable model-class identity review."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import (
    ModelClassMappingRepository,
    ModelVersionRepository,
)


@dataclass(frozen=True, slots=True)
class MappingReviewResult:
    """Trusted mapping identity returned after a successful review."""

    model_version_id: int
    class_id: int
    raw_class_name: str
    entity_id: int
    entity_code: str
    common_name: str
    verified_at: datetime


class PestMappingReviewService:
    """Require exact reviewer assertions before trusting a model class."""

    def __init__(self, session: AsyncSession) -> None:
        self._model_versions = ModelVersionRepository(session)
        self._mappings = ModelClassMappingRepository(session)

    async def verify(
        self,
        *,
        model_name: str,
        model_version: str,
        class_id: int,
        expected_raw_class_name: str,
        expected_entity_code: str,
        verified_by: str,
        review_note: str,
    ) -> MappingReviewResult:
        """Verify one exact model-version/class/entity tuple."""

        model = await self._model_versions.get_by_name_and_version(
            name=model_name,
            version=model_version,
        )
        if model is None:
            raise ValueError(
                f"Model version {model_name}:{model_version} is not registered."
            )
        resolved = await self._mappings.get_with_entity_for_update(
            model_version_id=model.id,
            class_id=class_id,
        )
        if resolved is None:
            raise ValueError(
                f"Class {class_id} has no mapping for model version {model.id}."
            )
        mapping, entity = resolved
        if entity is None:
            raise ValueError("The mapping has no pest entity to verify.")
        if mapping.raw_class_name != expected_raw_class_name:
            raise ValueError(
                "Expected raw class name does not match the stored model label."
            )
        if entity.entity_code != expected_entity_code:
            raise ValueError(
                "Expected entity code does not match the stored pest entity."
            )

        verified_at = datetime.now(UTC)
        mapping.mapping_status = "verified"
        mapping.verified_at = verified_at
        mapping.verified_by = verified_by
        mapping.review_note = review_note
        return MappingReviewResult(
            model_version_id=model.id,
            class_id=mapping.class_id,
            raw_class_name=mapping.raw_class_name,
            entity_id=entity.id,
            entity_code=entity.entity_code,
            common_name=entity.common_name,
            verified_at=verified_at,
        )
