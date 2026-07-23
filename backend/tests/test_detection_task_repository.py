"""Tests for detection task database operations."""

from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DetectionTask
from app.repositories import DetectionTaskRepository


async def test_create_adds_pending_task_to_session() -> None:
    """Creating a task should send one pending ORM object through the session."""

    session = AsyncMock(spec=AsyncSession)
    repository = DetectionTaskRepository(session)

    result = await repository.create(
        model_version_id=1,
        original_image_path="data/image/IP000000000.jpg",
    )

    session.add.assert_called_once_with(result)
    session.flush.assert_awaited_once_with()
    session.refresh.assert_awaited_once_with(result)
    assert result.model_version_id == 1
    assert result.status == "pending"
    assert result.annotated_image_path is None


async def test_get_by_id_returns_session_result() -> None:
    """The repository should return the task selected by its primary key."""

    existing = DetectionTask(
        model_version_id=1,
        original_image_path="data/image/IP000000000.jpg",
        annotated_image_path=None,
        status="pending",
        error_message=None,
        completed_at=None,
    )
    query_result = Mock()
    query_result.scalar_one_or_none.return_value = existing
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = query_result
    repository = DetectionTaskRepository(session)

    result = await repository.get_by_id(1)

    session.execute.assert_awaited_once()
    assert result is existing


async def test_list_page_returns_rows_and_total() -> None:
    """Pagination should return selected tasks and a separate total count."""

    existing = DetectionTask(
        model_version_id=1,
        original_image_path="data/image/IP000000000.jpg",
        annotated_image_path=None,
        status="pending",
        error_message=None,
        completed_at=None,
    )
    scalar_rows = Mock()
    scalar_rows.all.return_value = [existing]
    query_result = Mock()
    query_result.scalars.return_value = scalar_rows
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 1
    session.execute.return_value = query_result
    repository = DetectionTaskRepository(session)

    tasks, total = await repository.list_page(offset=0, limit=20)

    session.scalar.assert_awaited_once()
    session.execute.assert_awaited_once()
    assert tasks == [existing]
    assert total == 1
