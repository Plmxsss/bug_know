"""Tests for safe knowledge source file storage."""

from hashlib import sha256
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.services import DocumentStorage


def _storage(tmp_path: Path, **overrides) -> DocumentStorage:
    return DocumentStorage(
        Settings(_env_file=None, storage_dir=tmp_path, **overrides)
    )


def test_valid_markdown_is_stored_by_checksum(tmp_path: Path) -> None:
    """The untrusted original filename must not become the storage name."""

    content = b"# Rice pest\n\nReviewed source text."
    stored = _storage(tmp_path).validate_and_store(
        content=content,
        filename="../../source.md",
        content_type="text/markdown",
    )

    assert stored.absolute_path.is_file()
    assert stored.absolute_path.name == f"{sha256(content).hexdigest()}.md"
    assert stored.relative_path.startswith("uploads/documents/")
    assert stored.file_type == "md"


def test_document_extension_and_mime_must_match(tmp_path: Path) -> None:
    """Renaming arbitrary bytes to PDF must not pass declaration checks."""

    with pytest.raises(AppError) as captured:
        _storage(tmp_path).validate_and_store(
            content=b"plain text",
            filename="fake.pdf",
            content_type="text/plain",
        )

    assert captured.value.code == "UNSUPPORTED_DOCUMENT_FORMAT"


def test_text_document_requires_utf8(tmp_path: Path) -> None:
    """Unknown legacy encodings should be rejected instead of mis-decoded."""

    with pytest.raises(AppError) as captured:
        _storage(tmp_path).validate_and_store(
            content=b"\xff\xfe\x80",
            filename="source.txt",
            content_type="text/plain",
        )

    assert captured.value.code == "INVALID_DOCUMENT_ENCODING"


def test_pdf_requires_header_and_end_marker(tmp_path: Path) -> None:
    """A MIME declaration alone is not sufficient for PDF admission."""

    with pytest.raises(AppError) as captured:
        _storage(tmp_path).validate_and_store(
            content=b"%PDF-1.7\nmissing trailer",
            filename="source.pdf",
            content_type="application/pdf",
        )

    assert captured.value.code == "INVALID_DOCUMENT_CONTENT"
