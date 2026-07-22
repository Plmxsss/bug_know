"""Tests for the API's shared error response structure."""

from fastapi.testclient import TestClient

from app.core.exceptions import AppError
from app.main import create_app


def _assert_request_id_matches_header(response) -> None:
    request_id = response.json()["error"]["request_id"]
    assert request_id != "unknown"
    assert response.headers["X-Request-ID"] == request_id


def test_unknown_route_uses_standard_error_response() -> None:
    """A missing route should return the same public error structure."""

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    _assert_request_id_matches_header(response)


def test_invalid_query_parameter_lists_validation_details() -> None:
    """Invalid request data should identify the field that failed."""

    application = create_app()

    @application.get("/test/validation")
    async def validation_route(limit: int) -> dict[str, int]:
        return {"limit": limit}

    with TestClient(application) as client:
        response = client.get("/test/validation", params={"limit": "not-an-integer"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["location"] == ["query", "limit"]
    _assert_request_id_matches_header(response)


def test_app_error_preserves_safe_business_message() -> None:
    """Expected business errors should preserve their public code and message."""

    application = create_app()

    @application.get("/test/business-error")
    async def business_error_route() -> None:
        raise AppError(
            status_code=409,
            code="TASK_NOT_READY",
            message="The detection task is not ready.",
        )

    with TestClient(application) as client:
        response = client.get("/test/business-error")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_NOT_READY"
    assert response.json()["error"]["message"] == "The detection task is not ready."
    _assert_request_id_matches_header(response)


def test_unexpected_error_hides_internal_message() -> None:
    """Unexpected exceptions must not expose private implementation details."""

    application = create_app()

    @application.get("/test/unexpected-error")
    async def unexpected_error_route() -> None:
        raise RuntimeError("database password and private details")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/test/unexpected-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "password" not in response.text
    _assert_request_id_matches_header(response)
