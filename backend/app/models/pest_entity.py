"""ORM model for one normalized agricultural pest entity."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PestEntity(Base):
    """Represent one stable pest identity independent of model labels."""

    __tablename__ = "pest_entities"
    __table_args__ = (
        CheckConstraint(
            "knowledge_status IN ('missing', 'draft', 'reviewed')",
            name="ck_pest_entities_knowledge_status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_code: Mapped[str] = mapped_column(String(100), unique=True)
    common_name: Mapped[str] = mapped_column(String(200), unique=True)
    scientific_name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    knowledge_status: Mapped[str] = mapped_column(
        String(20),
        default="missing",
        server_default="missing",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
