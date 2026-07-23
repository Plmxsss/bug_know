"""Business rules for registering validated knowledge source files."""

from datetime import date

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models import KnowledgeDocument
from app.repositories.knowledge_document import KnowledgeDocumentRepository
from app.services.document_storage import StoredDocument


class KnowledgeDocumentService:
    """Register unique source files against existing pest entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = KnowledgeDocumentRepository(session)

    async def register(
        self,
        *,
        stored: StoredDocument,
        title: str,
        source_organization: str,
        source_url: str | None,
        publication_date: date | None,
        region: str | None,
        entity_ids: list[int],
    ) -> KnowledgeDocument:
        """Validate metadata and commit one uploaded document record."""

        clean_title = title.strip()
        clean_organization = source_organization.strip()
        if not clean_title or not clean_organization:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="DOCUMENT_METADATA_REQUIRED",
                message="Title and source organization cannot be blank.",
            )
        clean_entity_ids = sorted(set(entity_ids))
        if not clean_entity_ids:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="DOCUMENT_ENTITY_REQUIRED",
                message="At least one pest entity is required.",
            )

        async with self._session.begin():
            duplicate = await self._repository.get_by_checksum(
                stored.checksum_sha256
            )
            if duplicate is not None:
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    code="DOCUMENT_ALREADY_EXISTS",
                    message=f"The same document is already registered as {duplicate.id}.",
                )
            existing_ids = await self._repository.get_existing_entity_ids(
                clean_entity_ids
            )
            missing_ids = sorted(set(clean_entity_ids) - existing_ids)
            if missing_ids:
                raise AppError(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    code="PEST_ENTITY_NOT_FOUND",
                    message="One or more selected pest entities do not exist.",
                    details={"missing_entity_ids": missing_ids},
                )
            return await self._repository.create(
                title=clean_title,
                source_organization=clean_organization,
                source_url=source_url,
                publication_date=publication_date,
                region=region.strip() if region else None,
                file_path=stored.relative_path,
                file_type=stored.file_type,
                checksum_sha256=stored.checksum_sha256,
                entity_ids=clean_entity_ids,
            )
