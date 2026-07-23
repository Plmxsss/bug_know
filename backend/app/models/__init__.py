"""SQLAlchemy ORM models used by AgriGuard AI."""

from app.models.detection_object import DetectionObject
from app.models.detection_task import DetectionTask
from app.models.entity_alias import EntityAlias
from app.models.model_class_mapping import ModelClassMapping
from app.models.model_version import ModelVersion
from app.models.pest_entity import PestEntity

__all__ = [
    "DetectionObject",
    "DetectionTask",
    "EntityAlias",
    "ModelClassMapping",
    "ModelVersion",
    "PestEntity",
]
