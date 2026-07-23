"""Database access classes used by application services."""

from app.repositories.detection_object import DetectionObjectRepository
from app.repositories.detection_task import DetectionTaskRepository
from app.repositories.model_version import ModelVersionRepository

__all__ = [
    "DetectionObjectRepository",
    "DetectionTaskRepository",
    "ModelVersionRepository",
]
