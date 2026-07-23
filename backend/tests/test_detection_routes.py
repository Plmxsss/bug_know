"""Tests for detection task API routes."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.main import create_app
from app.models import DetectionTask


def _mock_session_with_task(task: DetectionTask | None) -> AsyncMock:
    query_result = Mock()
    query_result.scalar_one_or_none.return_value = task
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = query_result
    return session


def test_get_detection_task_returns_public_record() -> None:
    """The detail endpoint should serialize one ORM task as public JSON."""

    task = DetectionTask(
        id=1,
        model_version_id=1,
        original_image_path="data/image/IP000000000.jpg",
        annotated_image_path=None,
        status="pending",
        error_message=None,
        created_at=datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
        completed_at=None,
    )
    session = _mock_session_with_task(task)
    application = create_app()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session

    with TestClient(application) as client:
        response = client.get("/api/v1/detections/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["status"] == "pending"
    assert response.json()["original_image_path"] == "data/image/IP000000000.jpg"


def test_get_missing_detection_task_returns_standard_404() -> None:
    """A missing task should use the application's standard error response."""

    session = _mock_session_with_task(None)
    application = create_app()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session

    with TestClient(application) as client:
        response = client.get("/api/v1/detections/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DETECTION_TASK_NOT_FOUND"


def test_list_detection_tasks_returns_pagination_metadata() -> None:
    """The history endpoint should expose rows, total, page, and page size."""

    task = DetectionTask(
        id=1,
        model_version_id=1,
        original_image_path="data/image/IP000000000.jpg",
        annotated_image_path=None,
        status="pending",
        error_message=None,
        created_at=datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
        completed_at=None,
    )
    session = AsyncMock(spec=AsyncSession)
    application = create_app()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session

    with (
        TestClient(application) as client,
        patch(
            "app.api.routes.detections.DetectionTaskRepository.list_page",
            new=AsyncMock(return_value=([task], 1)),
        ),
    ):
        response = client.get(
            "/api/v1/detections",
            params={"page": 1, "page_size": 10},
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 10
    assert response.json()["items"][0]["id"] == 1
