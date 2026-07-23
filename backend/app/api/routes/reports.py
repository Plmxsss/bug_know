"""Routes for reading persisted diagnosis reports."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.api.serializers import diagnosis_report_response
from app.core.config import Settings
from app.rag.vector_database import VectorDatabaseGateway
from app.schemas import DiagnosisReportResponse
from app.services import DiagnosisReportService

router = APIRouter(prefix="/reports", tags=["diagnosis reports"])


@router.get(
    "/{task_id}",
    response_model=DiagnosisReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the completed diagnosis report for a detection task",
)
async def get_diagnosis_report(
    request: Request,
    task_id: Annotated[int, Path(ge=1)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DiagnosisReportResponse:
    """Read stored validated JSON without calling retrieval or an LLM again."""

    stored = await DiagnosisReportService(
        session=session,
        settings=cast(Settings, request.app.state.settings),
        vector_database=cast(
            VectorDatabaseGateway,
            request.app.state.vector_database,
        ),
        embedder=None,
        llm_provider=None,
    ).get_completed(task_id)
    return diagnosis_report_response(stored)
