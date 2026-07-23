"""ORM model that records a deployable YOLO model version."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelVersion(Base):
    """Describe one trained model artifact that the API may load."""

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "version",
            name="uq_model_versions_name_version",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(50))
    weights_path: Mapped[str] = mapped_column(String(500))
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    class_count: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
