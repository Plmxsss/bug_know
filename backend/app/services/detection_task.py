"""Business rules for detection task status changes."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.ml.predictors.types import Detection
from app.models import DetectionTask
from app.repositories import DetectionObjectRepository, DetectionTaskRepository


class DetectionTaskService:
    """Move detection tasks through valid processing states."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = DetectionTaskRepository(session)
        self._object_repository = DetectionObjectRepository(session)

    async def start(self, task_id: int) -> DetectionTask:
        """Move one pending task to processing."""

        async with self._session.begin():
            task = await self._get_locked_task(task_id)
            self._require_status(task, allowed={"pending"}, target="processing")
            task.status = "processing"
            return await self._repository.save(task)

    async def complete(
        self,
        task_id: int,
        *,
        annotated_image_path: str,
        detections: Sequence[Detection] = (),
        normalized_entity_ids: Mapping[int, int] | None = None,
    ) -> DetectionTask:
        """Atomically save detections and complete one processing task."""

        async with self._session.begin():
            task = await self._get_locked_task(task_id)
            self._require_status(task, allowed={"processing"}, target="completed")
            await self._object_repository.create_many(
                task_id=task_id,
                detections=detections,
                normalized_entity_ids=normalized_entity_ids,
            )
            task.status = "completed"
            task.annotated_image_path = annotated_image_path
            task.error_message = None
            task.completed_at = datetime.now(UTC)
            return await self._repository.save(task)

    async def fail(self, task_id: int, *, error_message: str) -> DetectionTask:
        """Mark one pending or processing task as failed."""

        clean_message = error_message.strip()
        if not clean_message:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="EMPTY_TASK_ERROR_MESSAGE",
                message="A failed detection task requires an error message.",
            )

        async with self._session.begin():
            task = await self._get_locked_task(task_id)
            self._require_status(
                task,
                allowed={"pending", "processing"},
                target="failed",
            )
            task.status = "failed"
            task.error_message = clean_message
            task.completed_at = datetime.now(UTC)
            return await self._repository.save(task)

    async def _get_locked_task(self, task_id: int) -> DetectionTask:
        """Load one task for modification or raise a public not-found error."""

        task = await self._repository.get_by_id_for_update(task_id)
        if task is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="DETECTION_TASK_NOT_FOUND",
                message=f"Detection task {task_id} does not exist.",
            )
        return task

    @staticmethod
    def _require_status(
        task: DetectionTask,
        *,
        allowed: set[str],
        target: str,
    ) -> None:
        """Reject a state change that is invalid for the current task."""

        if task.status not in allowed:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code="INVALID_TASK_STATUS_TRANSITION",
                message=(
                    f"Detection task cannot move from {task.status} to {target}."
                ),
                details={"current_status": task.status, "target_status": target},
            )
