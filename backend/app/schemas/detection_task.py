"""API response structures for detection tasks."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DetectionTaskResponse(BaseModel):
    """Public fields returned for one detection task."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    model_version_id: int
    annotated_image_url: str | None
    status: Literal["pending", "processing", "completed", "failed"]
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class DetectionTaskListResponse(BaseModel):
    """One page of detection task history and its pagination metadata."""

    items: list[DetectionTaskResponse]
    total: int
    page: int
    page_size: int


class BoundingBoxResponse(BaseModel):
    """One public rectangle in original-image pixel coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float


class DetectionResponse(BaseModel):
    """One public predictor result without framework-specific objects."""

    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBoxResponse
    normalization_status: Literal["unmapped", "needs_review", "verified"]
    normalized_entity_id: int | None
    entity_code: str | None
    common_name: str | None
    knowledge_status: Literal["missing", "draft", "reviewed"] | None


class DetectionCreateResponse(BaseModel):
    """Immediate result returned after a single-image detection finishes."""

    task_id: int
    status: Literal["completed"]
    detections: list[DetectionResponse]
    annotated_image_url: str
    inference_ms: float
    device: str


class StoredDetectionResponse(BaseModel):
    """One database-backed detection returned by the task detail endpoint."""

    object_id: int
    class_id: int
    raw_class_name: str
    normalized_entity_id: int | None
    confidence: float
    bbox: BoundingBoxResponse


class DetectionTaskDetailResponse(DetectionTaskResponse):
    """A task plus every persisted bounding box produced for its image."""

    detections: list[StoredDetectionResponse]
