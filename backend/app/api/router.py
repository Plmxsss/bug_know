"""Top-level router that gathers all version 1 API routes."""

from fastapi import APIRouter

from app.api.routes.detections import router as detections_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.questions import router as questions_router
from app.api.routes.reports import router as reports_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(detections_router)
api_router.include_router(documents_router)
api_router.include_router(knowledge_router)
api_router.include_router(reports_router)
api_router.include_router(questions_router)
