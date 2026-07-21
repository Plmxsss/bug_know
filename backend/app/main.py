"""FastAPI application entry point for AgriGuard AI."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    app_settings = settings or get_settings()
    application = FastAPI(
        title=app_settings.app_name,
        summary=app_settings.app_summary,
        version=app_settings.app_version,
    )
    application.include_router(api_router)
    return application


app = create_app()
