"""Ultralytics YOLO adapter that returns stable project prediction types."""

from pathlib import Path
from time import perf_counter
from typing import Any, cast

import torch
from ultralytics import YOLO  # type: ignore[attr-defined]

from app.ml.predictors.types import BoundingBox, Detection, PredictionResult


def _to_list(value: Any) -> list[Any]:
    """Move a tensor-like value to CPU and convert it to a Python list."""

    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    return list(value.tolist())


def parse_yolo_result(
    result: Any,
    *,
    elapsed_ms: float,
    device: str,
) -> PredictionResult:
    """Convert one Ultralytics result without leaking framework objects."""

    image_height, image_width = (int(value) for value in result.orig_shape)
    boxes = result.boxes
    detections: list[Detection] = []

    if boxes is not None:
        coordinates = _to_list(boxes.xyxy)
        confidences = _to_list(boxes.conf)
        class_ids = _to_list(boxes.cls)
        for xyxy, confidence, class_id_value in zip(
            coordinates,
            confidences,
            class_ids,
            strict=True,
        ):
            class_id = int(class_id_value)
            detections.append(
                Detection(
                    class_id=class_id,
                    class_name=str(result.names[class_id]),
                    confidence=float(confidence),
                    bbox=BoundingBox(
                        x1=float(xyxy[0]),
                        y1=float(xyxy[1]),
                        x2=float(xyxy[2]),
                        y2=float(xyxy[3]),
                    ),
                )
            )

    return PredictionResult(
        image_width=image_width,
        image_height=image_height,
        detections=tuple(detections),
        elapsed_ms=elapsed_ms,
        device=device,
    )


class YoloPredictor:
    """Load one YOLO weight once and run single-image pest detection."""

    def __init__(
        self,
        *,
        weights_path: Path,
        class_count: int,
        image_size: int = 640,
        device: str | None = None,
    ) -> None:
        if not weights_path.is_file():
            raise FileNotFoundError(f"YOLO weights do not exist: {weights_path}")

        self._device = device or ("0" if torch.cuda.is_available() else "cpu")
        self._image_size = image_size
        self._model = YOLO(str(weights_path))
        if self._model.task != "detect":
            raise ValueError(f"Expected a detection model, got {self._model.task}.")
        if len(self._model.names) != class_count:
            raise ValueError(
                f"Expected {class_count} classes, got {len(self._model.names)}."
            )

    @property
    def device(self) -> str:
        """Return the configured Ultralytics device value."""

        return self._device

    def predict(self, image_path: Path, *, confidence: float = 0.25) -> PredictionResult:
        """Run one synchronous prediction in original-image coordinates."""

        if not image_path.is_file():
            raise FileNotFoundError(f"Input image does not exist: {image_path}")
        if not 0.0 < confidence <= 1.0:
            raise ValueError("Confidence must be greater than 0 and at most 1.")

        started_at = perf_counter()
        results = cast(
            list[Any],
            self._model.predict(
                source=str(image_path),
                conf=confidence,
                imgsz=self._image_size,
                device=self._device,
                stream=False,
                verbose=False,
            ),
        )
        elapsed_ms = (perf_counter() - started_at) * 1000
        if len(results) != 1:
            raise RuntimeError(f"Expected one prediction result, got {len(results)}.")
        return parse_yolo_result(
            results[0],
            elapsed_ms=elapsed_ms,
            device=self._device,
        )
