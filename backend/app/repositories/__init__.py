"""Database access classes used by application services."""

from app.repositories.detection_object import DetectionObjectRepository
from app.repositories.detection_task import DetectionTaskRepository
from app.repositories.knowledge_document import KnowledgeDocumentRepository
from app.repositories.knowledge_review import KnowledgeReviewRepository
from app.repositories.knowledge_search import KnowledgeSearchRepository
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
    "KnowledgeDocumentRepository",
    "KnowledgeSearchRepository",
    "KnowledgeReviewRepository",
    "ModelClassMappingRepository",
    "ModelVersionRepository",
    "PestEntityRepository",
]
