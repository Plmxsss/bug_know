"""Environment-based application configuration."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
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
    yolo_enabled: bool = False
    yolo_weights_path: Path = Path(
        "data/runs/yolo26n_bug_know-5/weights/best.pt"
    )
    yolo_class_count: int = 102
    yolo_image_size: int = 640
    yolo_device: str = "0"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="AGRIGUARD_",
        extra="ignore",
    )


def get_settings() -> Settings:
    """Load application settings from defaults and environment variables."""

    return Settings()
