"""SQLAlchemy ORM models used by AgriGuard AI."""

from app.models.detection_object import DetectionObject
from app.models.detection_task import DetectionTask
from app.models.model_version import ModelVersion

__all__ = ["DetectionObject", "DetectionTask", "ModelVersion"]
