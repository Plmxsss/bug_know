"""Process-level health-check route."""

from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel

from app import __version__


class HealthResponse(BaseModel):
    """Public response returned by the health-check endpoint."""

    status: Literal["ok"]
    service: str
    version: str


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
