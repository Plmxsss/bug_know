"""Request and response structures for testing RAG retrieval."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

SearchQuery = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
]


class KnowledgeSearchRequest(BaseModel):
    """One entity-scoped semantic search."""

    entity_id: int = Field(ge=1)
    query: SearchQuery
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchHitResponse(BaseModel):
    """One returned chunk with enough provenance to display a citation."""

    point_id: str
    score: float
    document_id: int
    heading: str | None
    locator: str
    content: str
    title: str
    source_organization: str
    source_url: str | None
    publication_date: date | None
    region: str | None


class KnowledgeSearchResponse(BaseModel):
    """Ranked results and the review state of their entity scope."""

    entity_id: int
    common_name: str
    knowledge_status: Literal["missing", "draft", "reviewed"]
    hits: list[KnowledgeSearchHitResponse]
