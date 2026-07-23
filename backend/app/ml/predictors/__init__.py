"""Predictor interfaces and concrete model adapters."""

from app.ml.predictors.types import (
    BoundingBox,
    Detection,
    ImagePredictor,
    PredictionResult,
)

__all__ = [
    "BoundingBox",
    "Detection",
    "ImagePredictor",
    "PredictionResult",
]
