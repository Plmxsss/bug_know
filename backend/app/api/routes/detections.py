"""Routes for reading pest detection tasks."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.exceptions import AppError, ErrorResponse
from app.repositories import DetectionTaskRepository
from app.schemas import DetectionTaskListResponse, DetectionTaskResponse

router = APIRouter(prefix="/detections", tags=["detections"])


@router.get(
    "",
    response_model=DetectionTaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List detection task history",
)
async def list_detection_tasks(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DetectionTaskListResponse:
    """Return one newest-first page without exposing ORM objects."""

    repository = DetectionTaskRepository(session)
    tasks, total = await repository.list_page(
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return DetectionTaskListResponse(
        items=[DetectionTaskResponse.model_validate(task) for task in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{task_id}",
    response_model=DetectionTaskResponse,
    status_code=status.HTTP_200_OK,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get one detection task",
)
async def get_detection_task(
    task_id: Annotated[int, Path(ge=1)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DetectionTaskResponse:
    """Return one stored task without exposing internal database objects."""

    repository = DetectionTaskRepository(session)
    task = await repository.get_by_id(task_id)
    if task is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="DETECTION_TASK_NOT_FOUND",
            message=f"Detection task {task_id} does not exist.",
        )

    return DetectionTaskResponse.model_validate(task)
