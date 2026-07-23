"""Coordinate one stored image through model inference and persistence."""

import asyncio
import logging
from dataclasses import dataclass

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.exceptions import AppError
from app.ml.predictors.types import ImagePredictor, PredictionResult
from app.models import DetectionTask
from app.repositories import DetectionTaskRepository, ModelVersionRepository
from app.services.annotation_renderer import AnnotatedImage, AnnotationRenderer
from app.services.detection_task import DetectionTaskService
from app.services.entity_normalizer import EntityNormalization, EntityNormalizer
from app.services.image_storage import StoredImage

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DetectionRunResult:
    """Completed task data needed to build the upload API response."""

    task: DetectionTask
    prediction: PredictionResult
    annotated_image: AnnotatedImage
    normalizations: dict[int, EntityNormalization]


class DetectionRunService:
    """Orchestrate database state, synchronous GPU work, and image rendering."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        predictor: ImagePredictor,
        predictor_lock: asyncio.Lock,
        settings: Settings,
    ) -> None:
        self._session = session
        self._predictor = predictor
        self._predictor_lock = predictor_lock
        self._settings = settings
        self._task_repository = DetectionTaskRepository(session)
        self._model_repository = ModelVersionRepository(session)
        self._task_service = DetectionTaskService(session)
        self._normalizer = EntityNormalizer(session)
        self._renderer = AnnotationRenderer(settings)

    async def run(self, image: StoredImage) -> DetectionRunResult:
        """Create, execute, and complete one detection task."""

        task = await self._create_pending_task(image.relative_path)
        task_id = task.id
        model_version_id = task.model_version_id
        try:
            await self._task_service.start(task_id)
            async with self._predictor_lock:
                prediction = await run_in_threadpool(
                    self._predictor.predict,
                    image.absolute_path,
                    confidence=self._settings.yolo_confidence,
                )
            annotated = await run_in_threadpool(
                self._renderer.render,
                image=image,
                detections=prediction.detections,
            )
            async with self._session.begin():
                normalizations = await self._normalizer.normalize_many(
                    model_version_id=model_version_id,
                    detections=prediction.detections,
                )
            verified_entity_ids = {
                class_id: normalization.entity_id
                for class_id, normalization in normalizations.items()
                if normalization.status == "verified"
                and normalization.entity_id is not None
            }
            completed_task = await self._task_service.complete(
                task_id,
                annotated_image_path=annotated.relative_path,
                detections=prediction.detections,
                normalized_entity_ids=verified_entity_ids,
            )
            return DetectionRunResult(
                task=completed_task,
                prediction=prediction,
                annotated_image=annotated,
                normalizations=normalizations,
            )
        except Exception as exc:
            await self._session.rollback()
            await self._record_failure(task_id, exc)
            raise

    async def _create_pending_task(self, original_image_path: str) -> DetectionTask:
        """Resolve the configured active model and commit a pending task."""

        async with self._session.begin():
            model = await self._model_repository.get_active_by_name_and_version(
                name=self._settings.yolo_model_name,
                version=self._settings.yolo_model_version,
            )
            if model is None:
                raise AppError(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    code="ACTIVE_MODEL_NOT_REGISTERED",
                    message="The configured detection model is not active in the database.",
                )
            return await self._task_repository.create(
                model_version_id=model.id,
                original_image_path=original_image_path,
            )

    async def _record_failure(self, task_id: int, exc: Exception) -> None:
        """Best-effort failure recording without hiding the original exception."""

        message = f"{type(exc).__name__}: {exc}"[:2000]
        try:
            await self._task_service.fail(task_id, error_message=message)
        except Exception:
            logger.exception("Could not mark detection task %s as failed", task_id)
