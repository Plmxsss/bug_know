"""Environment-based application configuration."""

from pathlib import Path
from typing import Literal

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

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="AGRIGUARD_",
        extra="ignore",
    )


def get_settings() -> Settings:
    """Load application settings from defaults and environment variables."""

    return Settings()
