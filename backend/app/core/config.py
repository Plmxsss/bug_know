"""Environment-based application configuration."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Values that may change between development and deployment environments."""

    app_name: str = "AgriGuard AI API"
    app_summary: str = "Agricultural pest detection and knowledge API"
    app_version: str = __version__
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_database: str = "agriguard"
    mysql_user: str = "agriguard"
    mysql_password: SecretStr = SecretStr("")
    redis_host: str = "127.0.0.1"
    redis_port: int = 7379
    redis_database: int = Field(default=0, ge=0)
    redis_password: SecretStr = SecretStr("")
    redis_max_connections: int = Field(default=20, ge=1, le=1000)
    yolo_enabled: bool = False
    yolo_model_name: str = "ip102-yolo26n"
    yolo_model_version: str = "1.0.0"
    yolo_weights_path: Path = Path(
        "data/runs/yolo26n_bug_know-5/weights/best.pt"
    )
    yolo_class_count: int = 102
    yolo_image_size: int = 640
    yolo_device: str = "0"
    yolo_confidence: float = Field(default=0.25, gt=0.0, le=1.0)
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 25_000_000
    max_document_bytes: int = 20 * 1024 * 1024
    storage_dir: Path = Path("storage")
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "agriguard_knowledge"
    rag_chunk_size: int = Field(default=800, ge=200, le=4000)
    rag_chunk_overlap: int = Field(default=120, ge=0, le=1000)
    rag_top_k: int = Field(default=6, ge=1, le=20)
    embedding_enabled: bool = False
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_device: str = "cpu"
    embedding_dimension: int = Field(default=512, ge=1)
    embedding_batch_size: int = Field(default=16, ge=1, le=256)
    embedding_cache_dir: Path = Path("models/embeddings")
    llm_enabled: bool = False
    llm_provider: Literal["ollama", "openai-compatible"] = "ollama"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "qwen3:4b-instruct-2507-q4_K_M"
    llm_structured_mode: Literal[
        "json_schema",
        "json_object",
        "prompt_only",
    ] = "json_schema"
    llm_timeout_seconds: float = Field(default=120.0, gt=0.0, le=600.0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2048, ge=128, le=16384)
    agent_enabled: bool = False
    agent_rate_limit_requests: int = Field(default=5, ge=1, le=100)
    agent_rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="AGRIGUARD_",
        extra="ignore",
    )


def get_settings() -> Settings:
    """Load application settings from defaults and environment variables."""

    return Settings()
