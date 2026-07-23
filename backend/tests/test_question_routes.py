"""API boundary tests for optional bounded Agent questions."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import Settings
from app.main import create_app


class FakeRateRedis:
    """Return a fixed counter and capture the privacy-preserving key."""

    def __init__(self, count: int) -> None:
        self.count = count
        self.key = ""

    async def increment_with_expiry(
        self,
        *,
        key: str,
        ttl_seconds: int,
    ) -> int:
        assert ttl_seconds == 60
        self.key = key
        return self.count

    async def ping(self) -> None:
        return None

    async def close(self) -> None:
        return None


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


def test_question_endpoint_rate_limits_before_loading_models() -> None:
    """An over-limit request should stop before embedding and Agent setup."""

    redis = FakeRateRedis(count=6)
    settings = Settings(
        _env_file=None,
        agent_enabled=True,
        agent_rate_limit_requests=5,
        agent_rate_limit_window_seconds=60,
    )
    application = create_app(settings=settings, redis_gateway=redis)
    session = AsyncMock(spec=AsyncSession)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/detections/7/questions",
            json={"question": "它怎样危害水稻？"},
        )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "AGENT_RATE_LIMITED"
    assert response.json()["error"]["details"]["window_seconds"] == 60
    assert redis.key.startswith("rate:agent-question:7:")
    assert "testclient" not in redis.key
    session.execute.assert_not_awaited()
