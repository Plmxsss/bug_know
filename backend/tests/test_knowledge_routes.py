"""Tests for the public knowledge retrieval endpoint."""

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import Settings
from app.main import create_app


def _client(tmp_path: Path) -> TestClient:
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
    return TestClient(application)


def test_search_requires_enabled_embedding_model(tmp_path: Path) -> None:
    """A disabled local embedding model should produce an explicit 503."""

    with _client(tmp_path) as client:
        response = client.post(
            "/api/v1/knowledge/search",
            json={"entity_id": 1, "query": "How does it damage rice?"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "EMBEDDING_MODEL_DISABLED"


def test_search_rejects_blank_query_before_running_service(tmp_path: Path) -> None:
    """Whitespace is not a meaningful semantic-search query."""

    with _client(tmp_path) as client:
        response = client.post(
            "/api/v1/knowledge/search",
            json={"entity_id": 1, "query": "   "},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
