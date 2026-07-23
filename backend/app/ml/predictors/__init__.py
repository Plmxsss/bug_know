"""Predictor interfaces and concrete model adapters."""

from app.ml.predictors.types import (
    BoundingBox,
    Detection,
    ImagePredictor,
    PredictionResult,
)
from app.ml.predictors.yolo import YoloPredictor

__all__ = [
    "BoundingBox",
    "Detection",
    "ImagePredictor",
    "PredictionResult",
    "YoloPredictor",
]
