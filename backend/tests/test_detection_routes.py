"""Tests for detection task API routes."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import Settings
from app.main import create_app
from app.ml.predictors import BoundingBox, Detection, PredictionResult
from app.models import DetectionObject, DetectionTask
from app.services import AnnotatedImage, DetectionRunResult, EntityNormalization


def _mock_session_with_task(task: DetectionTask | None) -> AsyncMock:
    query_result = Mock()
    query_result.scalar_one_or_none.return_value = task
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = query_result
    return session


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (40, 30), color=(90, 150, 60)).save(buffer, format="PNG")
    return buffer.getvalue()


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

    detected_object = DetectionObject(
        id=5,
        task_id=1,
        class_id=0,
        raw_class_name="rice leaf folder",
        normalized_entity_id=None,
        confidence=0.69,
        bbox_x1=10.0,
        bbox_y1=20.0,
        bbox_x2=100.0,
        bbox_y2=120.0,
    )
    with (
        TestClient(application) as client,
        patch(
            "app.api.routes.detections.DetectionObjectRepository.list_by_task_id",
            new=AsyncMock(return_value=[detected_object]),
        ),
    ):
        response = client.get("/api/v1/detections/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["status"] == "pending"
    assert response.json()["detections"][0]["object_id"] == 5
    assert response.json()["detections"][0]["bbox"]["x2"] == 100.0
    assert "original_image_path" not in response.json()
    assert "annotated_image_path" not in response.json()


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
    assert "original_image_path" not in response.json()["items"][0]


def test_list_detection_tasks_hides_internal_failure_details() -> None:
    """Public history must not expose exception types or implementation text."""

    task = DetectionTask(
        id=5,
        model_version_id=1,
        original_image_path="uploads/original/private.jpg",
        annotated_image_path=None,
        status="failed",
        error_message="RuntimeError: CUDA secret internal diagnostic",
        created_at=datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 23, 12, 1, tzinfo=UTC),
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
        response = client.get("/api/v1/detections")

    assert response.status_code == 200
    public_error = response.json()["items"][0]["error_message"]
    assert public_error == "Detection failed. Check server logs with the task ID."
    assert "CUDA" not in public_error


def test_create_detection_returns_completed_prediction(tmp_path) -> None:
    """A valid upload should expose public detection data and an image URL."""

    settings = Settings(
        _env_file=None,
        yolo_enabled=True,
        storage_dir=tmp_path,
    )
    predictor = Mock()
    application = create_app(
        settings=settings,
        predictor_factory=lambda _settings: predictor,
    )
    session = AsyncMock(spec=AsyncSession)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session
    task = DetectionTask(id=44, status="completed")
    prediction = PredictionResult(
        image_width=40,
        image_height=30,
        detections=(
            Detection(
                class_id=3,
                class_name="pest",
                confidence=0.91,
                bbox=BoundingBox(x1=2.0, y1=3.0, x2=20.0, y2=25.0),
            ),
        ),
        elapsed_ms=12.5,
        device="0",
    )
    run_result = DetectionRunResult(
        task=task,
        prediction=prediction,
        annotated_image=AnnotatedImage(
            absolute_path=Path(tmp_path) / "result.png",
            relative_path="uploads/annotated/result.png",
        ),
        normalizations={
            3: EntityNormalization(
                class_id=3,
                raw_class_name="pest",
                status="needs_review",
                entity_id=None,
                entity_code=None,
                common_name=None,
                knowledge_status=None,
            )
        },
    )

    with (
        TestClient(application) as client,
        patch(
            "app.api.routes.detections.DetectionRunService.run",
            new=AsyncMock(return_value=run_result),
        ),
    ):
        response = client.post(
            "/api/v1/detections",
            files={"image": ("leaf.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 201
    assert response.json()["task_id"] == 44
    assert response.json()["detections"][0]["class_id"] == 3
    assert (
        response.json()["detections"][0]["normalization_status"]
        == "needs_review"
    )
    assert response.json()["annotated_image_url"] == "/media/annotated/result.png"


def test_create_detection_rejects_corrupted_image(tmp_path) -> None:
    """The route must stop before inference when image decoding fails."""

    settings = Settings(
        _env_file=None,
        yolo_enabled=True,
        storage_dir=tmp_path,
    )
    application = create_app(
        settings=settings,
        predictor_factory=lambda _settings: Mock(),
    )
    session = AsyncMock(spec=AsyncSession)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session
    run_mock = AsyncMock()
    with (
        TestClient(application) as client,
        patch(
            "app.api.routes.detections.DetectionRunService.run",
            new=run_mock,
        ),
    ):
        response = client.post(
            "/api/v1/detections",
            files={"image": ("fake.jpg", b"not-an-image", "image/jpeg")},
        )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "INVALID_IMAGE_CONTENT"
    run_mock.assert_not_awaited()


def test_create_detection_requires_enabled_model(tmp_path) -> None:
    """API-only deployments should explain that inference is unavailable."""

    settings = Settings(
        _env_file=None,
        yolo_enabled=False,
        storage_dir=tmp_path,
    )
    application = create_app(settings=settings)
    session = AsyncMock(spec=AsyncSession)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/detections",
            files={"image": ("leaf.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DETECTION_MODEL_DISABLED"
