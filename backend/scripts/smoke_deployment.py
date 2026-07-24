"""Verify the externally visible AgriGuard container stack."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import httpx

REQUIRED_OPENAPI_PATHS = {
    "/api/v1/detections",
    "/api/v1/detections/{task_id}",
    "/api/v1/detections/{task_id}/diagnosis",
    "/api/v1/documents",
    "/api/v1/documents/{document_id}/index",
    "/api/v1/knowledge/search",
    "/api/v1/reports/{task_id}",
}


class SmokeCheckError(RuntimeError):
    """Raised when one externally visible deployment contract is broken."""


@dataclass(frozen=True, slots=True)
class SmokeResult:
    """One successful deployment check."""

    name: str
    path: str


def _json_object(response: httpx.Response, *, check: str) -> dict[str, Any]:
    """Return one JSON object or raise a check-specific error."""
    try:
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SmokeCheckError(f"{check} failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise SmokeCheckError(f"{check} failed: expected a JSON object.")
    return payload


def run_smoke_checks(client: httpx.Client) -> list[SmokeResult]:
    """Check Nginx, Vue, FastAPI, dependencies, and the public API contract."""
    results: list[SmokeResult] = []

    try:
        frontend = client.get("/")
        frontend.raise_for_status()
    except httpx.HTTPError as exc:
        raise SmokeCheckError(f"Vue frontend failed: {exc}") from exc
    if "text/html" not in frontend.headers.get("content-type", ""):
        raise SmokeCheckError("Vue frontend failed: response is not HTML.")
    if 'id="app"' not in frontend.text:
        raise SmokeCheckError("Vue frontend failed: application mount element is missing.")
    results.append(SmokeResult("Vue through Nginx", "/"))

    health = _json_object(client.get("/api/v1/health"), check="FastAPI health")
    if health.get("status") != "ok" or health.get("service") != "agriguard-api":
        raise SmokeCheckError("FastAPI health failed: unexpected response fields.")
    results.append(SmokeResult("FastAPI health through Nginx", "/api/v1/health"))

    readiness = _json_object(
        client.get("/api/v1/health/ready"),
        check="Dependency readiness",
    )
    expected_readiness = {
        "status": "ready",
        "database": "ok",
        "vector_database": "ok",
        "redis": "ok",
    }
    if readiness != expected_readiness:
        raise SmokeCheckError("Dependency readiness failed: one or more services are not ready.")
    results.append(
        SmokeResult("MySQL, Qdrant, and Redis readiness", "/api/v1/health/ready")
    )

    openapi = _json_object(client.get("/openapi.json"), check="OpenAPI")
    paths = openapi.get("paths")
    if not isinstance(paths, dict):
        raise SmokeCheckError("OpenAPI failed: paths object is missing.")
    missing_paths = REQUIRED_OPENAPI_PATHS.difference(paths)
    if missing_paths:
        missing = ", ".join(sorted(missing_paths))
        raise SmokeCheckError(f"OpenAPI failed: required paths are missing: {missing}")
    results.append(SmokeResult("Public OpenAPI contract", "/openapi.json"))

    return results


def main() -> int:
    """Run smoke checks against one deployed Nginx endpoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8080",
        help="Public Nginx base URL (default: %(default)s).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout in seconds for each request (default: %(default)s).",
    )
    args = parser.parse_args()

    try:
        with httpx.Client(
            base_url=args.base_url.rstrip("/"),
            timeout=args.timeout,
            follow_redirects=True,
        ) as client:
            results = run_smoke_checks(client)
    except SmokeCheckError as exc:
        print(f"FAILED: {exc}")
        return 1
    except httpx.HTTPError as exc:
        print(f"FAILED: deployment is unreachable: {exc}")
        return 1

    for result in results:
        print(f"PASS: {result.name} ({result.path})")
    print(f"Deployment smoke test passed: {len(results)} checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
