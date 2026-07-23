"""Database operations for detection_tasks records."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DetectionTask


class DetectionTaskRepository:
    """Read and write detection task rows through one database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, task_id: int) -> DetectionTask | None:
        """Return one task by primary key, or None when it does not exist."""

        statement = select(DetectionTask).where(DetectionTask.id == task_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        model_version_id: int,
        original_image_path: str,
    ) -> DetectionTask:
        """Add a pending detection task and load its generated values."""

        task = DetectionTask(
            model_version_id=model_version_id,
            original_image_path=original_image_path,
            annotated_image_path=None,
            status="pending",
            error_message=None,
            completed_at=None,
        )
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task
