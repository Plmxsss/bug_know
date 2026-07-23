"""Routes for reading pest detection tasks."""

import asyncio
from typing import Annotated, cast

from fastapi import (
    APIRouter,
    Depends,
    File,
    Path,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_db_session
from app.core.config import Settings
from app.core.exceptions import AppError, ErrorResponse
from app.ml.predictors.types import ImagePredictor
from app.repositories import DetectionTaskRepository
from app.schemas import (
    BoundingBoxResponse,
    DetectionCreateResponse,
    DetectionResponse,
    DetectionTaskListResponse,
    DetectionTaskResponse,
)
from app.services import DetectionRunService, ImageStorage

router = APIRouter(prefix="/detections", tags=["detections"])


@router.post(
    "",
    response_model=DetectionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
    summary="Upload and detect one pest image",
)
async def create_detection(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    image: Annotated[UploadFile, File(description="JPEG, PNG, or WebP image")],
) -> DetectionCreateResponse:
    """Validate one image, run YOLO, and persist the completed result."""

    settings = cast(Settings, request.app.state.settings)
    predictor = cast(ImagePredictor | None, request.app.state.predictor)
    if predictor is None:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DETECTION_MODEL_DISABLED",
            message="The detection model is not enabled on this API instance.",
        )

    content = await image.read(settings.max_upload_bytes + 1)
    await image.close()
    stored = await run_in_threadpool(
        ImageStorage(settings).validate_and_store,
        content=content,
        filename=image.filename,
        content_type=image.content_type,
    )
    service = DetectionRunService(
        session=session,
        predictor=predictor,
        predictor_lock=cast(asyncio.Lock, request.app.state.predictor_lock),
        settings=settings,
    )
    result = await service.run(stored)
    return DetectionCreateResponse(
        task_id=result.task.id,
        status="completed",
        detections=[
            DetectionResponse(
                class_id=detection.class_id,
                class_name=detection.class_name,
                confidence=detection.confidence,
                bbox=BoundingBoxResponse(
                    x1=detection.bbox.x1,
                    y1=detection.bbox.y1,
                    x2=detection.bbox.x2,
                    y2=detection.bbox.y2,
                ),
            )
            for detection in result.prediction.detections
        ],
        annotated_image_url=(
            f"/media/annotated/{result.annotated_image.absolute_path.name}"
        ),
        inference_ms=result.prediction.elapsed_ms,
        device=result.prediction.device,
    )


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
