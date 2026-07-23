"""Tests for application-lifetime model loading."""

from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.ml.predictors.types import PredictionResult


class FakePredictor:
    """Small predictor replacement that never loads PyTorch."""

    def predict(
        self,
        image_path: Path,
        *,
        confidence: float = 0.25,
    ) -> PredictionResult:
        raise NotImplementedError


def test_enabled_predictor_loads_once_during_application_startup() -> None:
    """Multiple requests should share the model loaded by one lifespan."""

    settings = Settings(_env_file=None, yolo_enabled=True)
    predictor = FakePredictor()
    factory = Mock(return_value=predictor)
    application = create_app(settings=settings, predictor_factory=factory)

    with TestClient(application) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/health").status_code == 200
        assert application.state.predictor is predictor

    factory.assert_called_once_with(settings)
