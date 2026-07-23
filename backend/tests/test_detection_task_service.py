"""Tests for detection task status business rules."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models import DetectionTask
from app.services import DetectionTaskService


def _task(status: str = "pending") -> DetectionTask:
    return DetectionTask(
        id=1,
        model_version_id=1,
        original_image_path="data/image/IP000000000.jpg",
        annotated_image_path=None,
        status=status,
        error_message=None,
        completed_at=None,
    )


def _service_with_task(task: DetectionTask | None) -> DetectionTaskService:
    session = AsyncMock(spec=AsyncSession)
    service = DetectionTaskService(session)
    service._repository.get_by_id_for_update = AsyncMock(return_value=task)
    service._repository.save = AsyncMock(side_effect=lambda value: value)
    return service


async def test_start_moves_pending_task_to_processing() -> None:
    """A worker may claim a task that is still pending."""

    service = _service_with_task(_task())

    result = await service.start(1)

    assert result.status == "processing"


async def test_complete_records_output_and_completion_time() -> None:
    """A processing task may finish with an annotated image."""

    service = _service_with_task(_task("processing"))

    result = await service.complete(
        1,
        annotated_image_path="uploads/annotated/result.jpg",
    )

    assert result.status == "completed"
    assert result.annotated_image_path == "uploads/annotated/result.jpg"
    assert result.completed_at is not None


async def test_fail_requires_non_empty_message() -> None:
    """Failure records must explain why processing stopped."""

    service = _service_with_task(_task())

    with pytest.raises(AppError) as captured:
        await service.fail(1, error_message="   ")

    assert captured.value.code == "EMPTY_TASK_ERROR_MESSAGE"


async def test_complete_rejects_pending_task() -> None:
    """A task must start processing before it can complete."""

    service = _service_with_task(_task())

    with pytest.raises(AppError) as captured:
        await service.complete(
            1,
            annotated_image_path="uploads/annotated/result.jpg",
        )

    assert captured.value.status_code == 409
    assert captured.value.code == "INVALID_TASK_STATUS_TRANSITION"


async def test_start_reports_missing_task() -> None:
    """Status operations should distinguish a missing task from a conflict."""

    service = _service_with_task(None)

    with pytest.raises(AppError) as captured:
        await service.start(999)

    assert captured.value.status_code == 404
    assert captured.value.code == "DETECTION_TASK_NOT_FOUND"
