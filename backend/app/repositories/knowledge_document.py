"""Database operations for knowledge documents and entity associations."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    KnowledgeDocument,
    KnowledgeDocumentEntity,
    PestEntity,
    RagChunk,
)


@dataclass(frozen=True, slots=True)
class RagChunkInsert:
    """Values needed to persist one already-vectorized chunk."""

    pest_entity_id: int
    chunk_index: int
    heading: str | None
    locator: str
    content: str
    content_sha256: str
    qdrant_point_id: str


class KnowledgeDocumentRepository:
    """Store source provenance and its explicit pest entity scope."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_checksum(self, checksum_sha256: str) -> KnowledgeDocument | None:
        """Return an already registered byte-identical source."""

        result = await self._session.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.checksum_sha256 == checksum_sha256
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self,
        document_id: int,
    ) -> KnowledgeDocument | None:
        """Lock one document row for a lifecycle state transition."""

        result = await self._session.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.id == document_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_entity_ids(self, document_id: int) -> list[int]:
        """Return every entity explicitly associated with a source."""

        result = await self._session.execute(
            select(KnowledgeDocumentEntity.pest_entity_id)
            .where(KnowledgeDocumentEntity.document_id == document_id)
            .order_by(KnowledgeDocumentEntity.pest_entity_id)
        )
        return list(result.scalars().all())

    async def list_chunk_point_ids(self, document_id: int) -> list[str]:
        """Return vector point IDs currently owned by one document."""

        result = await self._session.execute(
            select(RagChunk.qdrant_point_id).where(
                RagChunk.document_id == document_id
            )
        )
        return list(result.scalars().all())

    async def get_existing_entity_ids(
        self,
        entity_ids: Sequence[int],
    ) -> set[int]:
        """Return which requested pest entity primary keys exist."""

        result = await self._session.execute(
            select(PestEntity.id).where(PestEntity.id.in_(entity_ids))
        )
        return set(result.scalars().all())

    async def create(
        self,
        *,
        title: str,
        source_organization: str,
        source_url: str | None,
        publication_date: date | None,
        region: str | None,
        file_path: str,
        file_type: str,
        checksum_sha256: str,
        entity_ids: Sequence[int],
    ) -> KnowledgeDocument:
        """Insert one uploaded source and all selected entity links."""

        document = KnowledgeDocument(
            title=title,
            source_organization=source_organization,
            source_url=source_url,
            publication_date=publication_date,
            region=region,
            file_path=file_path,
            file_type=file_type,
            checksum_sha256=checksum_sha256,
            status="uploaded",
            error_message=None,
        )
        self._session.add(document)
        await self._session.flush()
        self._session.add_all(
            [
                KnowledgeDocumentEntity(
                    document_id=document.id,
                    pest_entity_id=entity_id,
                )
                for entity_id in entity_ids
            ]
        )
        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def replace_chunks(
        self,
        *,
        document_id: int,
        chunks: Sequence[RagChunkInsert],
    ) -> list[RagChunk]:
        """Replace MySQL chunk metadata after Qdrant accepts deterministic points."""

        await self._session.execute(
            delete(RagChunk).where(RagChunk.document_id == document_id)
        )
        rows = [
            RagChunk(
                document_id=document_id,
                pest_entity_id=chunk.pest_entity_id,
                chunk_index=chunk.chunk_index,
                heading=chunk.heading,
                locator=chunk.locator,
                content=chunk.content,
                content_sha256=chunk.content_sha256,
                qdrant_point_id=chunk.qdrant_point_id,
            )
            for chunk in chunks
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return rows

    async def mark_entities_draft(self, entity_ids: Sequence[int]) -> None:
        """Expose indexed knowledge as draft without claiming human review."""

        result = await self._session.execute(
            select(PestEntity)
            .where(PestEntity.id.in_(entity_ids))
            .with_for_update()
        )
        for entity in result.scalars():
            if entity.knowledge_status == "missing":
                entity.knowledge_status = "draft"
        await self._session.flush()
