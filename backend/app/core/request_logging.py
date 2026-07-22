"""Request identification and access logging."""

import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response

logger = logging.getLogger("agriguard.request")


async def log_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Assign a request ID, call the route, and record the result."""

    request_id = str(uuid4())
    request.state.request_id = request_id
    started_at = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed request_id=%s method=%s path=%s status_code=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response
