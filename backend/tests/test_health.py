"""Tests for the process-level health endpoint."""

from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app


class FakeDatabase:
    """Controllable database replacement used without a real MySQL server."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.closed = False

    async def ping(self) -> None:
        if not self.available:
            raise ConnectionError("MySQL is unavailable")

    async def close(self) -> None:
        self.closed = True


class FakeVectorDatabase:
    """Controllable Qdrant replacement used without a network service."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.closed = False

    async def ping(self) -> None:
        if not self.available:
            raise ConnectionError("Qdrant is unavailable")

    async def close(self) -> None:
        self.closed = True


class FakeRedis:
    """Controllable Redis replacement with explicit lifecycle state."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.closed = False

    async def ping(self) -> None:
        if not self.available:
            raise ConnectionError("Redis is unavailable")

    async def close(self) -> None:
        self.closed = True


def test_health_check_returns_service_metadata() -> None:
    """The health endpoint should expose stable, typed service metadata."""

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "agriguard-api",
        "version": "0.1.0",
    }
    UUID(response.headers["X-Request-ID"])


def test_each_request_receives_a_different_request_id() -> None:
    """Separate requests should be traceable by separate identifiers."""

    with TestClient(create_app()) as client:
        first_response = client.get("/api/v1/health")
        second_response = client.get("/api/v1/health")

    assert first_response.headers["X-Request-ID"] != second_response.headers["X-Request-ID"]


def test_openapi_contains_health_endpoint() -> None:
    """FastAPI should include the endpoint in its generated OpenAPI schema."""

    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
    assert "/api/v1/health/ready" in response.json()["paths"]


def test_readiness_check_succeeds_when_database_answers() -> None:
    """Readiness should succeed after the database answers a minimal query."""

    database = FakeDatabase()
    vector_database = FakeVectorDatabase()
    redis = FakeRedis()
    with TestClient(
        create_app(
            database=database,
            vector_database=vector_database,
            redis_gateway=redis,
        )
    ) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "vector_database": "ok",
        "redis": "ok",
    }
    assert database.closed is True
    assert vector_database.closed is True
    assert redis.closed is True


def test_readiness_check_fails_safely_when_database_is_down() -> None:
    """Readiness should return 503 without exposing connection details."""

    database = FakeDatabase(available=False)
    vector_database = FakeVectorDatabase()
    redis = FakeRedis()
    with TestClient(
        create_app(
            database=database,
            vector_database=vector_database,
            redis_gateway=redis,
        )
    ) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "MySQL is unavailable" not in response.text


def test_readiness_fails_safely_when_qdrant_is_down() -> None:
    """A Qdrant outage should be distinguishable without leaking details."""

    database = FakeDatabase()
    vector_database = FakeVectorDatabase(available=False)
    redis = FakeRedis()
    with TestClient(
        create_app(
            database=database,
            vector_database=vector_database,
            redis_gateway=redis,
        )
    ) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "VECTOR_DATABASE_UNAVAILABLE"
    assert "Qdrant is unavailable" not in response.text


def test_readiness_fails_safely_when_redis_is_down() -> None:
    """A Redis outage should be distinct and hide connection details."""

    database = FakeDatabase()
    vector_database = FakeVectorDatabase()
    redis = FakeRedis(available=False)
    with TestClient(
        create_app(
            database=database,
            vector_database=vector_database,
            redis_gateway=redis,
        )
    ) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REDIS_UNAVAILABLE"
    assert "Redis is unavailable" not in response.text
