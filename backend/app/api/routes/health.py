"""Process-level health-check route."""

from typing import Literal

from fastapi import APIRouter, Request, status
from pydantic import BaseModel

from app import __version__
from app.core.exceptions import AppError
from app.db.session import DatabaseGateway
from app.rag.vector_database import VectorDatabaseGateway


class HealthResponse(BaseModel):
    """Public response returned by the health-check endpoint."""

    status: Literal["ok"]
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Response returned after required external services answer successfully."""

    status: Literal["ready"]
    database: Literal["ok"]
    vector_database: Literal["ok"]


router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check whether the API process is running",
)
async def health_check() -> HealthResponse:
    """Return process-level health without checking external dependencies."""

    return HealthResponse(
        status="ok",
        service="agriguard-api",
        version=__version__,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Check whether the API can reach its required services",
)
async def readiness_check(request: Request) -> ReadinessResponse:
    """Verify that MySQL can receive and execute a minimal query."""

    database: DatabaseGateway = request.app.state.database
    try:
        await database.ping()
    except Exception as exc:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATABASE_UNAVAILABLE",
            message="The database is currently unavailable.",
        ) from exc

    vector_database: VectorDatabaseGateway = request.app.state.vector_database
    try:
        await vector_database.ping()
    except Exception as exc:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="VECTOR_DATABASE_UNAVAILABLE",
            message="The vector database is currently unavailable.",
        ) from exc

    return ReadinessResponse(
        status="ready",
        database="ok",
        vector_database="ok",
    )
