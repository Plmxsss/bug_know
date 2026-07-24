"""Regression tests for the production container topology."""

from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_backend_dockerfile_exposes_optional_dependency_targets() -> None:
    """Keep the small API image separate from local embedding and YOLO layers."""
    dockerfile = (REPOSITORY_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

    assert "ARG PYTHON_BASE_IMAGE=python:3.11-slim" in dockerfile
    assert "FROM runtime-base AS api" in dockerfile
    assert "FROM api AS rag" in dockerfile
    assert "FROM rag AS full" in dockerfile
    assert 'python -m pip install ".[agent]"' in dockerfile
    assert 'python -m pip install ".[rag]"' in dockerfile
    assert 'python -m pip install ".[ml]"' in dockerfile


def test_compose_waits_for_persistent_services() -> None:
    """Require healthy stateful services before starting the API."""
    compose = yaml.safe_load(
        (REPOSITORY_ROOT / "infra" / "compose.yaml").read_text(encoding="utf-8")
    )
    services = compose["services"]
    backend = services["backend"]

    assert backend["build"]["target"] == "${AGRIGUARD_BACKEND_TARGET:-api}"
    assert backend["build"]["args"]["PYTHON_BASE_IMAGE"] == (
        "${AGRIGUARD_PYTHON_BASE_IMAGE:-python:3.11-slim}"
    )
    assert backend["depends_on"] == {
        "mysql": {"condition": "service_healthy"},
        "qdrant": {"condition": "service_healthy"},
        "redis": {"condition": "service_healthy"},
    }
    assert services["web"]["depends_on"] == {
        "backend": {"condition": "service_healthy"}
    }


def test_nginx_proxies_backend_and_supports_vue_routes() -> None:
    """Keep browser API URLs same-origin and preserve Vue history routing."""
    nginx = (REPOSITORY_ROOT / "infra" / "nginx.conf").read_text(encoding="utf-8")

    assert "location /api/" in nginx
    assert "location /media/" in nginx
    assert "location = /openapi.json" in nginx
    assert "proxy_pass http://backend:8000" in nginx
    assert "try_files $uri $uri/ /index.html;" in nginx
