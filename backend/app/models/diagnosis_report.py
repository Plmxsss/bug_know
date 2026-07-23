"""ORM model for one idempotent diagnosis report per detection task."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiagnosisReport(Base):
    """Track report generation state, validated JSON, and model metadata."""

    __tablename__ = "diagnosis_reports"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            name="uq_diagnosis_reports_task_id",
        ),
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="ck_diagnosis_reports_status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "detection_tasks.id",
            name="fk_diagnosis_reports_task_id_detection_tasks",
            ondelete="CASCADE",
        ),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="processing",
        server_default="processing",
    )
    llm_provider: Mapped[str | None] = mapped_column(String(100))
    llm_model: Mapped[str | None] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(100))
    report_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
