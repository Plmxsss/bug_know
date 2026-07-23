"""Tests for framework-independent YOLO output parsing."""

from types import SimpleNamespace

import numpy as np

from app.ml.predictors import BoundingBox
from app.ml.predictors.yolo import parse_yolo_result


def test_parse_yolo_result_converts_boxes_to_project_types() -> None:
    """Tensor-like YOLO fields should become typed Python values."""

    result = SimpleNamespace(
        orig_shape=(420, 650),
        names={0: "稻纵卷叶螟", 1: "稻叶毛虫"},
        boxes=SimpleNamespace(
            xyxy=np.array([[10.5, 20.0, 100.25, 200.75]], dtype=np.float32),
            conf=np.array([0.6903], dtype=np.float32),
            cls=np.array([0.0], dtype=np.float32),
        ),
    )

    parsed = parse_yolo_result(result, elapsed_ms=38.2, device="0")

    assert parsed.image_width == 650
    assert parsed.image_height == 420
    assert parsed.elapsed_ms == 38.2
    assert len(parsed.detections) == 1
    assert parsed.detections[0].class_id == 0
    assert parsed.detections[0].class_name == "稻纵卷叶螟"
    assert parsed.detections[0].bbox == BoundingBox(
        x1=10.5,
        y1=20.0,
        x2=100.25,
        y2=200.75,
    )


def test_parse_yolo_result_handles_no_detections() -> None:
    """An image with no accepted boxes should return an empty tuple."""

    result = SimpleNamespace(
        orig_shape=(480, 640),
        names={0: "稻纵卷叶螟"},
        boxes=SimpleNamespace(
            xyxy=np.empty((0, 4), dtype=np.float32),
            conf=np.empty((0,), dtype=np.float32),
            cls=np.empty((0,), dtype=np.float32),
        ),
    )

    parsed = parse_yolo_result(result, elapsed_ms=20.0, device="cpu")

    assert parsed.detections == ()
