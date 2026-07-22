"""FastAPI application entry point for AgriGuard AI."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.request_logging import log_request


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    application = FastAPI(
        title=app_settings.app_name,
        summary=app_settings.app_summary,
        version=app_settings.app_version,
    )
    application.middleware("http")(log_request)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
