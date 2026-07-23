"""Routes for reading pest detection tasks."""

import asyncio
from pathlib import PurePosixPath
from typing import Annotated, Literal, cast

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
from app.api.serializers import diagnosis_report_response
from app.core.config import Settings
from app.core.exceptions import AppError, ErrorResponse
from app.llm import LLMProvider
from app.ml.predictors.types import ImagePredictor
from app.models import DetectionTask
from app.rag.embeddings import TextEmbedder
from app.rag.vector_database import VectorDatabaseGateway
from app.repositories import DetectionObjectRepository, DetectionTaskRepository
from app.schemas import (
    BoundingBoxResponse,
    DetectionCreateResponse,
    DetectionResponse,
    DetectionTaskDetailResponse,
    DetectionTaskListResponse,
    DetectionTaskResponse,
    DiagnosisReportResponse,
    StoredDetectionResponse,
)
from app.services import DetectionRunService, DiagnosisReportService, ImageStorage

router = APIRouter(prefix="/detections", tags=["detections"])


def _annotated_image_url(path: str | None) -> str | None:
    """Convert an internal storage key to the only public image path."""

    if path is None:
        return None
    return f"/media/annotated/{PurePosixPath(path).name}"


def _task_response(task: DetectionTask) -> DetectionTaskResponse:
    """Serialize a task without exposing original or annotated storage keys."""

    return DetectionTaskResponse(
        id=task.id,
        model_version_id=task.model_version_id,
        annotated_image_url=_annotated_image_url(task.annotated_image_path),
        status=cast(
            Literal["pending", "processing", "completed", "failed"],
            task.status,
        ),
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


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
                normalization_status=result.normalizations[
                    detection.class_id
                ].status,
                normalized_entity_id=result.normalizations[
                    detection.class_id
                ].entity_id,
                entity_code=result.normalizations[detection.class_id].entity_code,
                common_name=result.normalizations[detection.class_id].common_name,
                knowledge_status=result.normalizations[
                    detection.class_id
                ].knowledge_status,
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
        items=[_task_response(task) for task in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{task_id}",
    response_model=DetectionTaskDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get one detection task",
)
async def get_detection_task(
    task_id: Annotated[int, Path(ge=1)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DetectionTaskDetailResponse:
    """Return one stored task without exposing internal database objects."""

    repository = DetectionTaskRepository(session)
    task = await repository.get_by_id(task_id)
    if task is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="DETECTION_TASK_NOT_FOUND",
            message=f"Detection task {task_id} does not exist.",
        )

    objects = await DetectionObjectRepository(session).list_by_task_id(task_id)
    task_response = _task_response(task)
    return DetectionTaskDetailResponse(
        **task_response.model_dump(),
        detections=[
            StoredDetectionResponse(
                object_id=detected_object.id,
                class_id=detected_object.class_id,
                raw_class_name=detected_object.raw_class_name,
                normalized_entity_id=detected_object.normalized_entity_id,
                confidence=detected_object.confidence,
                bbox=BoundingBoxResponse(
                    x1=detected_object.bbox_x1,
                    y1=detected_object.bbox_y1,
                    x2=detected_object.bbox_x2,
                    y2=detected_object.bbox_y2,
                ),
            )
            for detected_object in objects
        ],
    )


@router.post(
    "/{task_id}/diagnosis",
    response_model=DiagnosisReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate or return one evidence-bound diagnosis report",
)
async def create_diagnosis_report(
    request: Request,
    task_id: Annotated[int, Path(ge=1)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DiagnosisReportResponse:
    """Combine persisted detections, reviewed RAG evidence, and the configured LLM."""

    stored = await DiagnosisReportService(
        session=session,
        settings=cast(Settings, request.app.state.settings),
        vector_database=cast(
            VectorDatabaseGateway,
            request.app.state.vector_database,
        ),
        embedder=cast(TextEmbedder | None, request.app.state.embedder),
        llm_provider=cast(
            LLMProvider | None,
            request.app.state.llm_provider,
        ),
    ).generate(task_id)
    return diagnosis_report_response(stored)
