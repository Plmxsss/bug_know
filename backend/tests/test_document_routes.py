"""Tests for knowledge document upload API behavior."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import Settings
from app.main import create_app
from app.models import KnowledgeDocument


def test_upload_markdown_returns_registered_provenance(tmp_path: Path) -> None:
    """A valid source should return metadata without its internal file path."""

    settings = Settings(_env_file=None, storage_dir=tmp_path)
    application = create_app(settings=settings)
    session = AsyncMock(spec=AsyncSession)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session
    document = KnowledgeDocument(
        id=3,
        title="Rice pest guide",
        source_organization="Agriculture Institute",
        source_url="https://example.org/guide",
        publication_date=None,
        region="China",
        file_type="md",
        checksum_sha256="a" * 64,
        status="uploaded",
        created_at=datetime(2026, 7, 23, tzinfo=UTC),
    )
    with (
        TestClient(application) as client,
        patch(
            "app.api.routes.documents.KnowledgeDocumentService.register",
            new=AsyncMock(return_value=document),
        ),
    ):
        response = client.post(
            "/api/v1/documents",
            data={
                "title": "Rice pest guide",
                "source_organization": "Agriculture Institute",
                "source_url": "https://example.org/guide",
                "region": "China",
                "entity_ids": "1",
            },
            files={
                "file": (
                    "guide.md",
                    b"# Guide\n\nSource content.",
                    "text/markdown",
                )
            },
        )

    assert response.status_code == 201
    assert response.json()["id"] == 3
    assert response.json()["entity_ids"] == [1]
    assert "file_path" not in response.json()


def test_index_document_requires_enabled_embedding_model(tmp_path: Path) -> None:
    """API deployments without the RAG model should return a clear 503."""

    settings = Settings(
        _env_file=None,
        storage_dir=tmp_path,
        embedding_enabled=False,
    )
    application = create_app(settings=settings)
    session = AsyncMock(spec=AsyncSession)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session
    with TestClient(application) as client:
        response = client.post("/api/v1/documents/1/index")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "EMBEDDING_MODEL_DISABLED"
