"""API boundary tests for optional bounded Agent questions."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import Settings
from app.main import create_app


def _application() -> tuple[TestClient, AsyncMock]:
    settings = Settings(_env_file=None, agent_enabled=False)
    application = create_app(settings=settings)
    session = AsyncMock(spec=AsyncSession)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session
    return TestClient(application), session


def test_question_endpoint_requires_explicit_agent_enablement() -> None:
    """Deployments without optional Agent behavior should fail clearly."""

    client, _session = _application()
    with client:
        response = client.post(
            "/api/v1/detections/7/questions",
            json={"question": "它怎样危害水稻？"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AGENT_DISABLED"


def test_question_endpoint_rejects_too_short_question() -> None:
    """Pydantic should stop malformed input before Agent or database work."""

    client, session = _application()
    with client:
        response = client.post(
            "/api/v1/detections/7/questions",
            json={"question": "？"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    session.execute.assert_not_awaited()
