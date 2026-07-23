"""Tests for knowledge document registration business rules."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models import KnowledgeDocument
from app.services import KnowledgeDocumentService, StoredDocument


def _stored(tmp_path: Path) -> StoredDocument:
    return StoredDocument(
        absolute_path=tmp_path / "source.md",
        relative_path="uploads/documents/source.md",
        file_type="md",
        checksum_sha256="a" * 64,
        size_bytes=20,
    )


async def test_duplicate_document_is_rejected(tmp_path: Path) -> None:
    """Byte-identical sources should not create competing document IDs."""

    session = AsyncMock(spec=AsyncSession)
    service = KnowledgeDocumentService(session)
    service._repository.get_by_checksum = AsyncMock(
        return_value=KnowledgeDocument(id=7)
    )

    with pytest.raises(AppError) as captured:
        await service.register(
            stored=_stored(tmp_path),
            title="Guide",
            source_organization="Institute",
            source_url=None,
            publication_date=None,
            region=None,
            entity_ids=[1],
        )

    assert captured.value.status_code == 409
    assert captured.value.code == "DOCUMENT_ALREADY_EXISTS"


async def test_missing_entity_is_reported(tmp_path: Path) -> None:
    """Every metadata filter target must exist before document registration."""

    session = AsyncMock(spec=AsyncSession)
    service = KnowledgeDocumentService(session)
    service._repository.get_by_checksum = AsyncMock(return_value=None)
    service._repository.get_existing_entity_ids = AsyncMock(return_value={1})

    with pytest.raises(AppError) as captured:
        await service.register(
            stored=_stored(tmp_path),
            title="Guide",
            source_organization="Institute",
            source_url=None,
            publication_date=None,
            region=None,
            entity_ids=[1, 999],
        )

    assert captured.value.code == "PEST_ENTITY_NOT_FOUND"
    assert captured.value.details == {"missing_entity_ids": [999]}
