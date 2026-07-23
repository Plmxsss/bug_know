"""Tests for uploaded image validation and safe local storage."""

from io import BytesIO

import pytest
from PIL import Image

from app.core.config import Settings
from app.core.exceptions import AppError
from app.services import ImageStorage


def _image_bytes(
    *,
    image_format: str = "JPEG",
    size: tuple[int, int] = (32, 24),
) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color=(30, 120, 60)).save(buffer, format=image_format)
    return buffer.getvalue()


def _storage(tmp_path, **settings_overrides) -> ImageStorage:
    settings = Settings(
        _env_file=None,
        storage_dir=tmp_path,
        **settings_overrides,
    )
    return ImageStorage(settings)


def test_valid_jpeg_is_saved_under_generated_name(tmp_path) -> None:
    """An accepted image should not retain the untrusted original filename."""

    content = _image_bytes()
    stored = _storage(tmp_path).validate_and_store(
        content=content,
        filename="../../unsafe-name.jpg",
        content_type="image/jpeg",
    )

    assert stored.absolute_path.is_file()
    assert stored.absolute_path.read_bytes() == content
    assert stored.absolute_path.name != "unsafe-name.jpg"
    assert stored.absolute_path.suffix == ".jpg"
    assert stored.relative_path.startswith("uploads/original/")
    assert stored.width == 32
    assert stored.height == 24


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("image.exe", "image/jpeg"),
        ("image.jpg", "application/octet-stream"),
        ("image.png", "image/jpeg"),
    ],
)
def test_extension_mime_and_signature_must_match(
    tmp_path,
    filename: str,
    content_type: str,
) -> None:
    """Changing only a filename or MIME declaration must not bypass checks."""

    with pytest.raises(AppError) as captured:
        _storage(tmp_path).validate_and_store(
            content=_image_bytes(),
            filename=filename,
            content_type=content_type,
        )

    assert captured.value.status_code == 415
    assert captured.value.code == "UNSUPPORTED_IMAGE_FORMAT"


def test_corrupted_image_is_rejected(tmp_path) -> None:
    """A JPEG-like filename is insufficient when Pillow cannot decode bytes."""

    with pytest.raises(AppError) as captured:
        _storage(tmp_path).validate_and_store(
            content=b"not really an image",
            filename="fake.jpg",
            content_type="image/jpeg",
        )

    assert captured.value.code == "INVALID_IMAGE_CONTENT"


def test_upload_byte_limit_is_enforced_before_decoding(tmp_path) -> None:
    """Oversized content should be rejected without asking Pillow to open it."""

    content = _image_bytes()
    with pytest.raises(AppError) as captured:
        _storage(tmp_path, max_upload_bytes=len(content) - 1).validate_and_store(
            content=content,
            filename="large.jpg",
            content_type="image/jpeg",
        )

    assert captured.value.status_code == 413
    assert captured.value.code == "IMAGE_FILE_TOO_LARGE"


def test_pixel_limit_is_enforced(tmp_path) -> None:
    """A compressed but very wide image should still obey decoded pixel limits."""

    with pytest.raises(AppError) as captured:
        _storage(tmp_path, max_image_pixels=100).validate_and_store(
            content=_image_bytes(size=(20, 20)),
            filename="wide.jpg",
            content_type="image/jpeg",
        )

    assert captured.value.code == "IMAGE_PIXEL_LIMIT_EXCEEDED"
