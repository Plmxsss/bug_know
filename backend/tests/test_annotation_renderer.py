"""Tests for framework-independent detection image rendering."""

from io import BytesIO

from PIL import Image, ImageChops

from app.core.config import Settings
from app.ml.predictors import BoundingBox, Detection
from app.services import AnnotationRenderer, ImageStorage


def _stored_image(tmp_path):
    buffer = BytesIO()
    Image.new("RGB", (100, 80), color=(255, 255, 255)).save(buffer, format="PNG")
    settings = Settings(_env_file=None, storage_dir=tmp_path)
    stored = ImageStorage(settings).validate_and_store(
        content=buffer.getvalue(),
        filename="leaf.png",
        content_type="image/png",
    )
    return settings, stored


def test_renderer_creates_a_changed_annotated_copy(tmp_path) -> None:
    """A detection should add visible pixels while preserving the source file."""

    settings, stored = _stored_image(tmp_path)
    original_bytes = stored.absolute_path.read_bytes()
    detection = Detection(
        class_id=4,
        class_name="pest",
        confidence=0.876,
        bbox=BoundingBox(x1=10.0, y1=15.0, x2=70.0, y2=60.0),
    )

    annotated = AnnotationRenderer(settings).render(
        image=stored,
        detections=(detection,),
    )

    assert annotated.absolute_path.is_file()
    assert annotated.relative_path.startswith("uploads/annotated/")
    assert stored.absolute_path.read_bytes() == original_bytes
    with (
        Image.open(stored.absolute_path) as original,
        Image.open(annotated.absolute_path) as rendered,
    ):
        assert ImageChops.difference(
            original.convert("RGB"),
            rendered.convert("RGB"),
        ).getbbox() is not None


def test_renderer_still_creates_output_when_nothing_is_detected(tmp_path) -> None:
    """The API needs a displayable result image even for an empty detection."""

    settings, stored = _stored_image(tmp_path)

    annotated = AnnotationRenderer(settings).render(
        image=stored,
        detections=(),
    )

    assert annotated.absolute_path.is_file()
