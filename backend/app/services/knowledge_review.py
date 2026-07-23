"""Promote pest knowledge only after explicit evidence checks."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import KnowledgeReviewRepository, PestEntityRepository


@dataclass(frozen=True, slots=True)
class KnowledgeReviewResult:
    """Audited knowledge state and the documents supporting the decision."""

    entity_id: int
    entity_code: str
    common_name: str
    document_ids: tuple[int, ...]
    source_organizations: tuple[str, ...]
    reviewed_at: datetime


class KnowledgeReviewService:
    """Require source quantity, diversity, provenance, and reviewer assertions."""

    def __init__(self, session: AsyncSession) -> None:
        self._entities = PestEntityRepository(session)
        self._evidence = KnowledgeReviewRepository(session)

    async def review(
        self,
        *,
        entity_code: str,
        expected_common_name: str,
        reviewed_by: str,
        review_note: str,
        minimum_documents: int = 2,
    ) -> KnowledgeReviewResult:
        """Mark one entity reviewed after objective prerequisites pass."""

        entity = await self._entities.get_by_code_for_update(entity_code)
        if entity is None:
            raise ValueError(f"Pest entity {entity_code!r} does not exist.")
        if entity.common_name != expected_common_name:
            raise ValueError(
                "Expected common name does not match the stored pest entity."
            )
        evidence = await self._evidence.list_indexed_source_evidence(entity.id)
        if len(evidence) < minimum_documents:
            raise ValueError(
                f"Knowledge review requires at least {minimum_documents} "
                "indexed documents with retrievable chunks."
            )
        organizations = tuple(
            sorted({item.source_organization for item in evidence})
        )
        if len(organizations) < 2:
            raise ValueError(
                "Knowledge review requires at least two source organizations."
            )
        if any(not item.source_url for item in evidence):
            raise ValueError(
                "Every reviewed knowledge document must have a source URL."
            )

        reviewed_at = datetime.now(UTC)
        entity.knowledge_status = "reviewed"
        entity.knowledge_reviewed_at = reviewed_at
        entity.knowledge_reviewed_by = reviewed_by
        entity.knowledge_review_note = review_note
        return KnowledgeReviewResult(
            entity_id=entity.id,
            entity_code=entity.entity_code,
            common_name=entity.common_name,
            document_ids=tuple(item.document_id for item in evidence),
            source_organizations=organizations,
            reviewed_at=reviewed_at,
        )
