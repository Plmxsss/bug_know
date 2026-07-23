"""Validate knowledge source files and store them by content checksum."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from fastapi import status

from app.core.config import PROJECT_ROOT, Settings
from app.core.exceptions import AppError


@dataclass(frozen=True, slots=True)
class DocumentFormatRule:
    """Declarations accepted for one supported knowledge file type."""

    content_types: frozenset[str]
    extensions: frozenset[str]
    file_type: str
    stored_extension: str


DOCUMENT_FORMAT_RULES = (
    DocumentFormatRule(
        content_types=frozenset({"application/pdf"}),
        extensions=frozenset({".pdf"}),
        file_type="pdf",
        stored_extension=".pdf",
    ),
    DocumentFormatRule(
        content_types=frozenset({"text/plain"}),
        extensions=frozenset({".txt"}),
        file_type="txt",
        stored_extension=".txt",
    ),
    DocumentFormatRule(
        content_types=frozenset({"text/markdown", "text/plain"}),
        extensions=frozenset({".md", ".markdown"}),
        file_type="md",
        stored_extension=".md",
    ),
)


@dataclass(frozen=True, slots=True)
class StoredDocument:
    """Validated source file information used by document persistence."""

    absolute_path: Path
    relative_path: str
    file_type: str
    checksum_sha256: str
    size_bytes: int


class DocumentStorage:
    """Reject misleading files and keep accepted bytes under stable names."""

    def __init__(self, settings: Settings) -> None:
        storage_root = settings.storage_dir
        if not storage_root.is_absolute():
            storage_root = PROJECT_ROOT / storage_root
        self._storage_root = storage_root
        self._document_dir = storage_root / "uploads" / "documents"
        self._max_document_bytes = settings.max_document_bytes

    def validate_and_store(
        self,
        *,
        content: bytes,
        filename: str | None,
        content_type: str | None,
    ) -> StoredDocument:
        """Validate a complete upload and store one checksum-addressed copy."""

        if not content:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="EMPTY_DOCUMENT_FILE",
                message="The uploaded document is empty.",
            )
        if len(content) > self._max_document_bytes:
            raise AppError(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                code="DOCUMENT_FILE_TOO_LARGE",
                message=f"The document exceeds {self._max_document_bytes} bytes.",
            )
        if not filename:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="MISSING_DOCUMENT_FILENAME",
                message="The uploaded document requires a filename.",
            )

        suffix = Path(filename).suffix.lower()
        rule = next(
            (
                candidate
                for candidate in DOCUMENT_FORMAT_RULES
                if suffix in candidate.extensions
                and content_type in candidate.content_types
            ),
            None,
        )
        if rule is None:
            raise AppError(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code="UNSUPPORTED_DOCUMENT_FORMAT",
                message="Only matching PDF, UTF-8 TXT, and Markdown files are supported.",
            )
        self._validate_content(content, file_type=rule.file_type)

        checksum = sha256(content).hexdigest()
        self._document_dir.mkdir(parents=True, exist_ok=True)
        absolute_path = self._document_dir / f"{checksum}{rule.stored_extension}"
        if not absolute_path.exists():
            absolute_path.write_bytes(content)
        return StoredDocument(
            absolute_path=absolute_path,
            relative_path=absolute_path.relative_to(self._storage_root).as_posix(),
            file_type=rule.file_type,
            checksum_sha256=checksum,
            size_bytes=len(content),
        )

    @staticmethod
    def _validate_content(content: bytes, *, file_type: str) -> None:
        """Check simple signatures now; full parsing happens during indexing."""

        if file_type == "pdf":
            if not content.startswith(b"%PDF-") or not content.rstrip().endswith(
                b"%%EOF"
            ):
                raise AppError(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    code="INVALID_DOCUMENT_CONTENT",
                    message="The uploaded PDF signature is invalid.",
                )
            return

        if b"\x00" in content:
            raise AppError(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code="INVALID_DOCUMENT_CONTENT",
                message="Text documents cannot contain null bytes.",
            )
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AppError(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code="INVALID_DOCUMENT_ENCODING",
                message="Text documents must use UTF-8 encoding.",
            ) from exc
