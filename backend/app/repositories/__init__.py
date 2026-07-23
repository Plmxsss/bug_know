"""Database access classes used by application services."""

from app.repositories.detection_object import DetectionObjectRepository
from app.repositories.detection_task import DetectionTaskRepository
from app.repositories.model_version import ModelVersionRepository
from app.repositories.pest_normalization import (
    EntityAliasRepository,
    ModelClassMappingRepository,
    PestEntityRepository,
)

__all__ = [
    "DetectionObjectRepository",
    "DetectionTaskRepository",
    "EntityAliasRepository",
    "ModelClassMappingRepository",
    "ModelVersionRepository",
    "PestEntityRepository",
]
