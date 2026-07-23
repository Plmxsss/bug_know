"""FastAPI application entry point for AgriGuard AI."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.cache import RedisClient, RedisGateway
from app.core.config import PROJECT_ROOT, Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.request_logging import log_request
from app.db.session import Database, DatabaseGateway
from app.llm import LLMProvider, OpenAICompatibleProvider
from app.ml.predictors.types import ImagePredictor
from app.rag.embeddings import SentenceTransformerEmbedder, TextEmbedder
from app.rag.vector_database import QdrantVectorDatabase, VectorDatabaseGateway

PredictorFactory = Callable[[Settings], ImagePredictor]
EmbedderFactory = Callable[[Settings], TextEmbedder]


def load_yolo_predictor(settings: Settings) -> ImagePredictor:
    """Import and load YOLO only when the deployment enables ML inference."""

    os.environ.setdefault(
        "MPLCONFIGDIR",
        str(PROJECT_ROOT / ".cache" / "matplotlib"),
    )
    from app.ml.predictors.yolo import YoloPredictor

    weights_path = settings.yolo_weights_path
    if not weights_path.is_absolute():
        weights_path = PROJECT_ROOT / weights_path
    return YoloPredictor(
        weights_path=weights_path,
        class_count=settings.yolo_class_count,
        image_size=settings.yolo_image_size,
        device=settings.yolo_device,
    )


def load_text_embedder(settings: Settings) -> TextEmbedder:
    """Load the optional local embedding model only for RAG-enabled deployments."""

    return SentenceTransformerEmbedder(settings)


def create_app(
    settings: Settings | None = None,
    database: DatabaseGateway | None = None,
    vector_database: VectorDatabaseGateway | None = None,
    redis_gateway: RedisGateway | None = None,
    llm_provider: LLMProvider | None = None,
    predictor_factory: PredictorFactory | None = None,
    embedder_factory: EmbedderFactory | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""

    app_settings = settings or get_settings()
    app_database = database or Database(app_settings)
    app_vector_database = vector_database or QdrantVectorDatabase(app_settings)
    app_redis = redis_gateway or RedisClient(app_settings)
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Keep shared resources available until the application stops."""

        application.state.database = app_database
        application.state.vector_database = app_vector_database
        application.state.redis = app_redis
        application.state.settings = app_settings
        application.state.predictor_lock = asyncio.Lock()
        if not hasattr(application.state, "predictor"):
            application.state.predictor = (
                (predictor_factory or load_yolo_predictor)(app_settings)
                if app_settings.yolo_enabled
                else None
            )
        if not hasattr(application.state, "embedder"):
            application.state.embedder = (
                (embedder_factory or load_text_embedder)(app_settings)
                if app_settings.embedding_enabled
                else None
            )
        if not hasattr(application.state, "llm_provider"):
            application.state.llm_provider = (
                llm_provider
                or (
                    OpenAICompatibleProvider(app_settings)
                    if app_settings.llm_enabled
                    else None
                )
            )
        yield
        try:
            if application.state.llm_provider is not None:
                await application.state.llm_provider.close()
        finally:
            try:
                await app_redis.close()
            finally:
                try:
                    await app_vector_database.close()
                finally:
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
    storage_root = app_settings.storage_dir
    if not storage_root.is_absolute():
        storage_root = PROJECT_ROOT / storage_root
    application.mount(
        "/media/annotated",
        StaticFiles(
            directory=storage_root / "uploads" / "annotated",
            check_dir=False,
        ),
        name="annotated-images",
    )
    return application


app = create_app()
