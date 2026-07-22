"""FastAPI application entry point for AgriGuard AI."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.request_logging import log_request
from app.db.session import Database, DatabaseGateway


def create_app(
    settings: Settings | None = None,
    database: DatabaseGateway | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""

    app_settings = settings or get_settings()
    app_database = database or Database(app_settings)
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Keep shared resources available until the application stops."""

        application.state.database = app_database
        yield
        await app_database.close()

    application = FastAPI(
        title=app_settings.app_name,
        summary=app_settings.app_summary,
        version=app_settings.app_version,
        lifespan=lifespan,
    )
    application.middleware("http")(log_request)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
