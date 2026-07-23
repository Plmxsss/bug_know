"""Tests for environment-based application configuration."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_settings_use_safe_defaults() -> None:
    """The API should have useful defaults when no override is provided."""

    settings = Settings(_env_file=None)

    assert settings.app_name == "AgriGuard AI API"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.mysql_host == "127.0.0.1"
    assert settings.mysql_password.get_secret_value() == ""
    assert settings.yolo_enabled is False
    assert settings.yolo_class_count == 102


def test_environment_variable_overrides_default(monkeypatch) -> None:
    """An environment variable should replace its matching default value."""

    monkeypatch.setenv("AGRIGUARD_APP_NAME", "AgriGuard Test API")

    settings = Settings(_env_file=None)

    assert settings.app_name == "AgriGuard Test API"


def test_database_password_is_hidden_when_settings_are_printed() -> None:
    """Configuration output must not accidentally reveal the database password."""

    settings = Settings(_env_file=None, mysql_password="private-password")

    assert "private-password" not in str(settings)


def test_create_app_uses_given_settings() -> None:
    """The application factory should use explicitly supplied settings."""

    settings = Settings(
        _env_file=None,
        app_name="AgriGuard Test API",
        app_version="9.9.9",
        environment="test",
    )

    with TestClient(create_app(settings)) as client:
        openapi = client.get("/openapi.json").json()

    assert openapi["info"]["title"] == "AgriGuard Test API"
    assert openapi["info"]["version"] == "9.9.9"
