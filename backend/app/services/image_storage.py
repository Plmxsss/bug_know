"""Validate uploaded image bytes and store them under safe generated names."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import status
from PIL import Image, UnidentifiedImageError
from PIL.Image import open as open_image

from app.core.config import PROJECT_ROOT, Settings
from app.core.exceptions import AppError


@dataclass(frozen=True, slots=True)
class ImageFormatRule:
    """Allowed declarations and safe output suffix for one decoded format."""

    content_types: frozenset[str]
    extensions: frozenset[str]
    stored_extension: str


FORMAT_RULES: dict[str, ImageFormatRule] = {
    "JPEG": ImageFormatRule(
        content_types=frozenset({"image/jpeg"}),
        extensions=frozenset({".jpg", ".jpeg"}),
        stored_extension=".jpg",
    ),
    "PNG": ImageFormatRule(
        content_types=frozenset({"image/png"}),
        extensions=frozenset({".png"}),
        stored_extension=".png",
    ),
    "WEBP": ImageFormatRule(
        content_types=frozenset({"image/webp"}),
        extensions=frozenset({".webp"}),
        stored_extension=".webp",
    ),
}


@dataclass(frozen=True, slots=True)
class StoredImage:
    """Validated image information needed by detection processing."""

    absolute_path: Path
    relative_path: str
    width: int
    height: int
    image_format: str
    size_bytes: int


class ImageStorage:
    """Apply upload safety rules and write accepted bytes to local storage."""

    def __init__(self, settings: Settings) -> None:
        storage_root = settings.storage_dir
        if not storage_root.is_absolute():
            storage_root = PROJECT_ROOT / storage_root
        self._storage_root = storage_root
        self._original_dir = storage_root / "uploads" / "original"
        self._max_upload_bytes = settings.max_upload_bytes
        self._max_image_pixels = settings.max_image_pixels

    def validate_and_store(
        self,
        *,
        content: bytes,
        filename: str | None,
        content_type: str | None,
    ) -> StoredImage:
        """Validate one complete upload and save it under a UUID filename."""

        if not content:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="EMPTY_IMAGE_FILE",
                message="The uploaded image is empty.",
            )
        if len(content) > self._max_upload_bytes:
            raise AppError(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                code="IMAGE_FILE_TOO_LARGE",
                message=f"The image exceeds {self._max_upload_bytes} bytes.",
            )
        if not filename:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="MISSING_IMAGE_FILENAME",
                message="The uploaded image requires a filename.",
            )

        try:
            with open_image(BytesIO(content)) as image:
                image_format = str(image.format).upper()
                width, height = image.size
                image.verify()
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
            raise AppError(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code="INVALID_IMAGE_CONTENT",
                message="The uploaded file is not a decodable image.",
            ) from exc

        rules = FORMAT_RULES.get(image_format)
        suffix = Path(filename).suffix.lower()
        if (
            rules is None
            or suffix not in rules.extensions
            or content_type not in rules.content_types
        ):
            raise AppError(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code="UNSUPPORTED_IMAGE_FORMAT",
                message="Only matching JPEG, PNG, and WebP uploads are supported.",
            )
        if width * height > self._max_image_pixels:
            raise AppError(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                code="IMAGE_PIXEL_LIMIT_EXCEEDED",
                message=f"The image exceeds {self._max_image_pixels} pixels.",
            )

        self._original_dir.mkdir(parents=True, exist_ok=True)
        absolute_path = self._original_dir / f"{uuid4().hex}{rules.stored_extension}"
        absolute_path.write_bytes(content)
        return StoredImage(
            absolute_path=absolute_path,
            relative_path=absolute_path.relative_to(self._storage_root).as_posix(),
            width=width,
            height=height,
            image_format=image_format,
            size_bytes=len(content),
        )
