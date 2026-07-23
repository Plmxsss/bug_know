"""Database operations for detection_tasks records."""

from sqlalchemy import func, select
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

    async def list_page(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[DetectionTask], int]:
        """Return one newest-first task page and the total row count."""

        count_statement = select(func.count()).select_from(DetectionTask)
        total = await self._session.scalar(count_statement)

        page_statement = (
            select(DetectionTask)
            .order_by(DetectionTask.created_at.desc(), DetectionTask.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(page_statement)
        tasks = list(result.scalars().all())
        return tasks, int(total or 0)

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
