"""Validated structures for evidence-bound pest diagnosis reports."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
]
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


class EntityKnowledgeSynthesis(BaseModel):
    """Only the explanatory fields the language model is allowed to generate."""

    introduction: NonBlankText
    typical_features: NonBlankText
    host_plants: list[ShortText] = Field(max_length=30)
    damage: NonBlankText
    environmental_conditions: NonBlankText
    prevention: list[NonBlankText] = Field(max_length=20)
    control_methods: list[NonBlankText] = Field(max_length=20)
    uncertainty: NonBlankText
    citation_point_ids: list[str] = Field(min_length=1, max_length=20)


class DiagnosisReference(BaseModel):
    """Citation rebuilt from trusted retrieval metadata, not model prose."""

    point_id: str
    document_id: int
    title: str
    source_organization: str
    source_url: str | None
    publication_date: str | None
    region: str | None
    locator: str


class DiagnosedEntity(BaseModel):
    """Deterministic detection facts combined with generated synthesis."""

    entity_id: int
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    count: int = Field(ge=1)
    introduction: str
    typical_features: str
    host_plants: list[str]
    damage: str
    environmental_conditions: str
    prevention: list[str]
    control_methods: list[str]
    uncertainty: str
    citation_point_ids: list[str]


class DiagnosisReportContent(BaseModel):
    """Complete report content suitable for persistence and API output."""

    summary: str
    detected_entities: list[DiagnosedEntity]
    references: list[DiagnosisReference]
    disclaimer: str


class DiagnosisUsage(BaseModel):
    """Token counts returned by a local or cloud-compatible provider."""

    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


class DiagnosisReportResponse(BaseModel):
    """Public persisted report with no internal error or prompt text."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    status: Literal["completed"]
    llm_provider: str
    llm_model: str
    prompt_version: str
    report: DiagnosisReportContent
    usage: DiagnosisUsage
    created_at: datetime
    completed_at: datetime
