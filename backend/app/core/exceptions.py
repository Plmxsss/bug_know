"""Application exceptions and their HTTP response handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorBody(BaseModel):
    """Details that explain why a request failed."""

    code: str
    message: str
    request_id: str
    details: Any = None


class ErrorResponse(BaseModel):
    """Stable outer structure used by every error response."""

    error: ErrorBody


class AppError(Exception):
    """Expected business error that can be safely shown to an API caller."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def _request_id(request: Request) -> str:
    """Read the ID assigned by request logging, with a safe fallback."""

    return str(getattr(request.state, "request_id", "unknown"))


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: object = None,
) -> JSONResponse:
    """Build one JSON error response and repeat its request ID in a header."""

    request_id = _request_id(request)
    content = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
        headers={"X-Request-ID": request_id},
    )


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return an expected business error without exposing internal details."""

    assert isinstance(exc, AppError)
    return _error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Explain which request values failed validation."""

    assert isinstance(exc, RequestValidationError)
    details = [
        {
            "location": [str(part) for part in error["loc"]],
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return _error_response(
        request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="The request data is invalid.",
        details=details,
    )


async def http_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Normalize errors such as an unknown route or unsupported method."""

    assert isinstance(exc, StarletteHTTPException)
    code_by_status = {
        404: "RESOURCE_NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
    }
    return _error_response(
        request,
        status_code=exc.status_code,
        code=code_by_status.get(exc.status_code, "HTTP_ERROR"),
        message=str(exc.detail),
    )


async def unexpected_error_handler(request: Request, _exc: Exception) -> JSONResponse:
    """Hide unexpected internal exception details from API callers."""

    return _error_response(
        request,
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal error occurred.",
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Register every error handler on one FastAPI application."""

    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
