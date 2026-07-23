"""Database operations for detection_objects records."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.predictors.types import Detection
from app.models import DetectionObject


class DetectionObjectRepository:
    """Store and retrieve the bounding boxes belonging to detection tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(
        self,
        *,
        task_id: int,
        detections: Sequence[Detection],
    ) -> list[DetectionObject]:
        """Convert predictor results to ORM rows and flush them together."""

        objects = [
            DetectionObject(
                task_id=task_id,
                class_id=detection.class_id,
                raw_class_name=detection.class_name,
                normalized_entity_id=None,
                confidence=detection.confidence,
                bbox_x1=detection.bbox.x1,
                bbox_y1=detection.bbox.y1,
                bbox_x2=detection.bbox.x2,
                bbox_y2=detection.bbox.y2,
            )
            for detection in detections
        ]
        if not objects:
            return []

        self._session.add_all(objects)
        await self._session.flush()
        return objects

    async def list_by_task_id(self, task_id: int) -> list[DetectionObject]:
        """Return one task's detections in stable primary-key order."""

        statement = (
            select(DetectionObject)
            .where(DetectionObject.task_id == task_id)
            .order_by(DetectionObject.id)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
