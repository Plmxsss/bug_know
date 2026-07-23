"""API response structures for knowledge source documents."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class KnowledgeDocumentResponse(BaseModel):
    """Public metadata returned after a document is registered."""

    id: int
    title: str
    source_organization: str
    source_url: str | None
    publication_date: date | None
    region: str | None
    file_type: Literal["pdf", "txt", "md"]
    checksum_sha256: str
    status: Literal["uploaded", "processing", "indexed", "failed"]
    entity_ids: list[int]
    created_at: datetime
