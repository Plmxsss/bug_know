"""Public request and response structures used by the API."""

from app.schemas.detection_task import (
    BoundingBoxResponse,
    DetectionCreateResponse,
    DetectionResponse,
    DetectionTaskListResponse,
    DetectionTaskResponse,
)

__all__ = [
    "BoundingBoxResponse",
    "DetectionCreateResponse",
    "DetectionResponse",
    "DetectionTaskListResponse",
    "DetectionTaskResponse",
]
