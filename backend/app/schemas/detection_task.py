"""API response structures for detection tasks."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DetectionTaskResponse(BaseModel):
    """Public fields returned for one detection task."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    model_version_id: int
    original_image_path: str
    annotated_image_path: str | None
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
