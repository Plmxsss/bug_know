"""Tests for the external deployment smoke-test script."""

import httpx
import pytest

from scripts.smoke_deployment import (
    REQUIRED_OPENAPI_PATHS,
    SmokeCheckError,
    run_smoke_checks,
)


def _success_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/":
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text='<html><div id="app"></div></html>',
        )
    if request.url.path == "/api/v1/health":
        return httpx.Response(
            200,
            json={"status": "ok", "service": "agriguard-api", "version": "0.1.0"},
        )
    if request.url.path == "/api/v1/health/ready":
        return httpx.Response(
            200,
            json={
                "status": "ready",
                "database": "ok",
                "vector_database": "ok",
                "redis": "ok",
            },
        )
    if request.url.path == "/openapi.json":
        return httpx.Response(
            200,
            json={"openapi": "3.1.0", "paths": dict.fromkeys(REQUIRED_OPENAPI_PATHS, {})},
        )
    return httpx.Response(404)


def test_smoke_checks_cover_public_stack() -> None:
    client = httpx.Client(
        base_url="http://deployment.test",
        transport=httpx.MockTransport(_success_handler),
    )

    results = run_smoke_checks(client)

    assert [result.name for result in results] == [
        "Vue through Nginx",
        "FastAPI health through Nginx",
        "MySQL, Qdrant, and Redis readiness",
        "Public OpenAPI contract",
    ]


def test_smoke_checks_reject_unready_dependency() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/health/ready":
            return httpx.Response(
                503,
                json={
                    "error": {
                        "code": "DATABASE_UNAVAILABLE",
                        "message": "The database is currently unavailable.",
                    }
                },
            )
        return _success_handler(request)

    client = httpx.Client(
        base_url="http://deployment.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SmokeCheckError, match="Dependency readiness failed"):
        run_smoke_checks(client)
