"""ORM model that records one image detection task."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DetectionTask(Base):
    """Track the lifecycle and files of one pest detection request."""

    __tablename__ = "detection_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_detection_tasks_status",
        ),
        Index(
            "ix_detection_tasks_model_version_id",
            "model_version_id",
        ),
        Index(
            "ix_detection_tasks_status_created_at",
            "status",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "model_versions.id",
            name="fk_detection_tasks_model_version_id_model_versions",
            ondelete="RESTRICT",
        ),
    )
    original_image_path: Mapped[str] = mapped_column(String(500))
    annotated_image_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
