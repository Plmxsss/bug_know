"""Shared conversions from service values to public API schemas."""

from app.schemas import DiagnosisReportResponse, DiagnosisUsage
from app.services import StoredDiagnosisReport


def diagnosis_report_response(
    stored: StoredDiagnosisReport,
) -> DiagnosisReportResponse:
    """Convert one validated service value without exposing ORM internals."""

    return DiagnosisReportResponse(
        id=stored.id,
        task_id=stored.task_id,
        status=stored.status,
        llm_provider=stored.llm_provider,
        llm_model=stored.llm_model,
        prompt_version=stored.prompt_version,
        report=stored.report,
        usage=DiagnosisUsage(
            prompt_tokens=stored.usage.prompt_tokens,
            completion_tokens=stored.usage.completion_tokens,
            total_tokens=stored.usage.total_tokens,
        ),
        created_at=stored.created_at,
        completed_at=stored.completed_at,
    )
