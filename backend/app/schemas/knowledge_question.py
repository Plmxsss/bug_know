"""Structures for bounded Agent retrieval and evidence-backed answers."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.diagnosis import DiagnosisReference

QuestionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=500),
]
AnswerText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
]


class KnowledgeQuestionRequest(BaseModel):
    """One follow-up question about pests in an existing detection task."""

    question: QuestionText


class KnowledgeQuestionSynthesis(BaseModel):
    """Only fields produced by the post-Agent structured generation step."""

    answer: AnswerText
    uncertainty: AnswerText
    citation_point_ids: list[str] = Field(min_length=1, max_length=20)


class KnowledgeQuestionResponse(BaseModel):
    """Public answer with observed Agent queries and trusted references."""

    task_id: int
    question: str
    planned_queries: list[str]
    answer: str
    uncertainty: str
    references: list[DiagnosisReference]
