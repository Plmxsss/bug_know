"""Collect indexed-source evidence used by knowledge review."""

from dataclasses import dataclass

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeDocument, KnowledgeDocumentEntity, RagChunk


@dataclass(frozen=True, slots=True)
class IndexedSourceEvidence:
    """One independently registered source with retrievable chunks."""

    document_id: int
    source_organization: str
    source_url: str | None


class KnowledgeReviewRepository:
    """Inspect source diversity without changing review state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_indexed_source_evidence(
        self,
        entity_id: int,
    ) -> list[IndexedSourceEvidence]:
        """Return indexed documents that have at least one entity-owned chunk."""

        has_chunk = exists(
            select(RagChunk.id).where(
                RagChunk.document_id == KnowledgeDocument.id,
                RagChunk.pest_entity_id == entity_id,
            )
        )
        result = await self._session.execute(
            select(
                KnowledgeDocument.id,
                KnowledgeDocument.source_organization,
                KnowledgeDocument.source_url,
            )
            .join(
                KnowledgeDocumentEntity,
                KnowledgeDocumentEntity.document_id == KnowledgeDocument.id,
            )
            .where(
                KnowledgeDocumentEntity.pest_entity_id == entity_id,
                KnowledgeDocument.status == "indexed",
                has_chunk,
            )
            .order_by(KnowledgeDocument.id)
        )
        return [
            IndexedSourceEvidence(
                document_id=row.id,
                source_organization=row.source_organization,
                source_url=row.source_url,
            )
            for row in result.all()
        ]
