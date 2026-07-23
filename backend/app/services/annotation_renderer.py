"""Render project prediction results onto validated images."""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import ImageDraw
from PIL.Image import open as open_image

from app.core.config import PROJECT_ROOT, Settings
from app.ml.predictors.types import Detection
from app.services.image_storage import StoredImage


@dataclass(frozen=True, slots=True)
class AnnotatedImage:
    """Paths of one generated image that is safe to expose through the API."""

    absolute_path: Path
    relative_path: str


class AnnotationRenderer:
    """Draw bounding boxes without depending on Ultralytics result objects."""

    def __init__(self, settings: Settings) -> None:
        storage_root = settings.storage_dir
        if not storage_root.is_absolute():
            storage_root = PROJECT_ROOT / storage_root
        self._storage_root = storage_root
        self._annotated_dir = storage_root / "uploads" / "annotated"

    def render(
        self,
        *,
        image: StoredImage,
        detections: tuple[Detection, ...],
    ) -> AnnotatedImage:
        """Draw detections and save a new image, leaving the original unchanged."""

        with open_image(image.absolute_path) as source:
            canvas = source.convert("RGB")

        draw = ImageDraw.Draw(canvas)
        line_width = max(2, round(min(image.width, image.height) / 200))
        for detection in detections:
            self._draw_detection(
                draw,
                detection=detection,
                image_width=image.width,
                image_height=image.height,
                line_width=line_width,
            )

        suffix = image.absolute_path.suffix.lower()
        self._annotated_dir.mkdir(parents=True, exist_ok=True)
        absolute_path = self._annotated_dir / f"{uuid4().hex}{suffix}"
        if image.image_format in {"JPEG", "WEBP"}:
            canvas.save(absolute_path, format=image.image_format, quality=90)
        else:
            canvas.save(absolute_path, format=image.image_format)
        return AnnotatedImage(
            absolute_path=absolute_path,
            relative_path=absolute_path.relative_to(self._storage_root).as_posix(),
        )

    @staticmethod
    def _draw_detection(
        draw: ImageDraw.ImageDraw,
        *,
        detection: Detection,
        image_width: int,
        image_height: int,
        line_width: int,
    ) -> None:
        """Draw one clamped rectangle and an ASCII label Pillow can always render."""

        x1 = min(max(detection.bbox.x1, 0.0), float(image_width - 1))
        y1 = min(max(detection.bbox.y1, 0.0), float(image_height - 1))
        x2 = min(max(detection.bbox.x2, x1 + 1.0), float(image_width))
        y2 = min(max(detection.bbox.y2, y1 + 1.0), float(image_height))
        color = (35, 220, 80)
        draw.rectangle((x1, y1, x2, y2), outline=color, width=line_width)

        label = f"class {detection.class_id}  {detection.confidence:.2f}"
        left, top, right, bottom = draw.textbbox((x1, y1), label)
        label_height = bottom - top + 4
        label_top = max(0.0, y1 - label_height)
        draw.rectangle(
            (x1, label_top, x1 + (right - left) + 4, y1),
            fill=color,
        )
        draw.text((x1 + 2, label_top + 1), label, fill=(0, 0, 0))
