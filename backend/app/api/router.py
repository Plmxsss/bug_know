"""Top-level router that gathers all version 1 API routes."""

from fastapi import APIRouter

from app.api.routes.detections import router as detections_router
from app.api.routes.health import router as health_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(detections_router)
