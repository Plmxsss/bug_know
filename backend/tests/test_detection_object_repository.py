"""Tests for detection object database operations."""

from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.predictors import BoundingBox, Detection
from app.models import DetectionObject
from app.repositories import DetectionObjectRepository


def _detection() -> Detection:
    return Detection(
        class_id=7,
        class_name="rice leafhopper",
        confidence=0.81,
        bbox=BoundingBox(x1=10.0, y1=20.0, x2=80.0, y2=100.0),
    )


async def test_create_many_converts_predictions_to_rows() -> None:
    """Predictor dataclasses should become task-linked ORM records."""

    session = AsyncMock(spec=AsyncSession)
    repository = DetectionObjectRepository(session)

    objects = await repository.create_many(task_id=12, detections=[_detection()])

    session.add_all.assert_called_once_with(objects)
    session.flush.assert_awaited_once_with()
    assert len(objects) == 1
    assert objects[0].task_id == 12
    assert objects[0].class_id == 7
    assert objects[0].confidence == 0.81
    assert objects[0].normalized_entity_id is None
    assert objects[0].bbox_x2 == 80.0


async def test_create_many_skips_database_for_empty_results() -> None:
    """An image with no detections should not perform an empty insert."""

    session = AsyncMock(spec=AsyncSession)
    repository = DetectionObjectRepository(session)

    objects = await repository.create_many(task_id=12, detections=[])

    assert objects == []
    session.add_all.assert_not_called()
    session.flush.assert_not_awaited()


async def test_list_by_task_id_returns_selected_rows() -> None:
    """The repository should unwrap ORM rows selected for one task."""

    existing = DetectionObject(
        task_id=12,
        class_id=7,
        raw_class_name="rice leafhopper",
        normalized_entity_id=None,
        confidence=0.81,
        bbox_x1=10.0,
        bbox_y1=20.0,
        bbox_x2=80.0,
        bbox_y2=100.0,
    )
    scalar_rows = Mock()
    scalar_rows.all.return_value = [existing]
    query_result = Mock()
    query_result.scalars.return_value = scalar_rows
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = query_result
    repository = DetectionObjectRepository(session)

    objects = await repository.list_by_task_id(12)

    session.execute.assert_awaited_once()
    assert objects == [existing]
