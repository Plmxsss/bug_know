"""Tests for the process-level health endpoint."""

from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app


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
