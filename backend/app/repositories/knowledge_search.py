"""Read indexed chunks and provenance after vector candidate selection."""

from dataclasses import dataclass
from datetime import date
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeDocument, PestEntity, RagChunk

KnowledgeStatus = Literal["missing", "draft", "reviewed"]


@dataclass(frozen=True, slots=True)
class PestKnowledgeScope:
    """Entity identity and its current human-review state."""

    id: int
    common_name: str
    knowledge_status: KnowledgeStatus


@dataclass(frozen=True, slots=True)
class StoredKnowledgeChunk:
    """Authoritative MySQL text and citation metadata for one vector point."""

    point_id: str
    document_id: int
    heading: str | None
    locator: str
    content: str
    title: str
    source_organization: str
    source_url: str | None
    publication_date: date | None
    region: str | None


class KnowledgeSearchRepository:
    """Resolve entities and validate Qdrant candidates against MySQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_scope(self, entity_id: int) -> PestKnowledgeScope | None:
        """Return one entity without exposing an ORM object outside the query."""

        result = await self._session.execute(
            select(
                PestEntity.id,
                PestEntity.common_name,
                PestEntity.knowledge_status,
            ).where(PestEntity.id == entity_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        return PestKnowledgeScope(
            id=row.id,
            common_name=row.common_name,
            knowledge_status=cast(KnowledgeStatus, row.knowledge_status),
        )

    async def get_chunks_by_point_ids(
        self,
        *,
        entity_id: int,
        point_ids: list[str],
    ) -> dict[str, StoredKnowledgeChunk]:
        """Return indexed chunks matching both point ID and entity ownership."""

        if not point_ids:
            return {}
        result = await self._session.execute(
            select(RagChunk, KnowledgeDocument)
            .join(
                KnowledgeDocument,
                KnowledgeDocument.id == RagChunk.document_id,
            )
            .where(
                RagChunk.qdrant_point_id.in_(point_ids),
                RagChunk.pest_entity_id == entity_id,
                KnowledgeDocument.status == "indexed",
            )
        )
        return {
            chunk.qdrant_point_id: StoredKnowledgeChunk(
                point_id=chunk.qdrant_point_id,
                document_id=document.id,
                heading=chunk.heading,
                locator=chunk.locator,
                content=chunk.content,
                title=document.title,
                source_organization=document.source_organization,
                source_url=document.source_url,
                publication_date=document.publication_date,
                region=document.region,
            )
            for chunk, document in result.all()
        }
