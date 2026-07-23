"""Validated structures for evidence-bound pest diagnosis reports."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

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
