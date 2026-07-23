"""Database operations for knowledge documents and entity associations."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    KnowledgeDocument,
    KnowledgeDocumentEntity,
    PestEntity,
)


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
