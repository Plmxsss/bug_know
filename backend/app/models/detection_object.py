"""ORM model for one bounding box produced by a detection task."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DetectionObject(Base):
    """Persist one raw YOLO detection in original-image coordinates."""

    __tablename__ = "detection_objects"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_detection_objects_confidence",
        ),
        CheckConstraint(
            "bbox_x1 >= 0 AND bbox_y1 >= 0 "
            "AND bbox_x2 > bbox_x1 AND bbox_y2 > bbox_y1",
            name="ck_detection_objects_bbox",
        ),
        Index("ix_detection_objects_task_id", "task_id"),
        Index(
            "ix_detection_objects_normalized_entity_id",
            "normalized_entity_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "detection_tasks.id",
            name="fk_detection_objects_task_id_detection_tasks",
            ondelete="CASCADE",
        ),
    )
    class_id: Mapped[int] = mapped_column(Integer)
    raw_class_name: Mapped[str] = mapped_column(String(200))
    normalized_entity_id: Mapped[int | None] = mapped_column(BigInteger)
    confidence: Mapped[float] = mapped_column(Float)
    bbox_x1: Mapped[float] = mapped_column(Float)
    bbox_y1: Mapped[float] = mapped_column(Float)
    bbox_x2: Mapped[float] = mapped_column(Float)
    bbox_y2: Mapped[float] = mapped_column(Float)
