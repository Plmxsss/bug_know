"""Stable prediction types independent of a model framework."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """One box in original-image pixel coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True, slots=True)
class Detection:
    """One detected object after model postprocessing."""

    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox


@dataclass(frozen=True, slots=True)
class PredictionResult:
    """Framework-independent result returned for one input image."""

    image_width: int
    image_height: int
    detections: tuple[Detection, ...]
    elapsed_ms: float
    device: str


class ImagePredictor(Protocol):
    """Prediction behavior required by application services."""

    def predict(
        self,
        image_path: Path,
        *,
        confidence: float = 0.25,
    ) -> PredictionResult:
        """Run one image prediction."""

        ...
