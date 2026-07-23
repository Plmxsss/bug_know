"""ORM model connecting one model class ID to a normalized pest entity."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelClassMapping(Base):
    """Track normalization and human-review state for one model label."""

    __tablename__ = "model_class_mappings"
    __table_args__ = (
        UniqueConstraint(
            "model_version_id",
            "class_id",
            name="uq_model_class_mappings_model_class",
        ),
        CheckConstraint(
            "class_id >= 0",
            name="ck_model_class_mappings_class_id",
        ),
        CheckConstraint(
            "mapping_status IN ('unmapped', 'needs_review', 'verified')",
            name="ck_model_class_mappings_status",
        ),
        Index("ix_model_class_mappings_entity_id", "pest_entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "model_versions.id",
            name="fk_model_class_mappings_model_version_id_model_versions",
            ondelete="CASCADE",
        ),
    )
    class_id: Mapped[int] = mapped_column(Integer)
    raw_class_name: Mapped[str] = mapped_column(String(200))
    pest_entity_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "pest_entities.id",
            name="fk_model_class_mappings_entity_id_pest_entities",
            ondelete="SET NULL",
        ),
    )
    mapping_status: Mapped[str] = mapped_column(
        String(20),
        default="unmapped",
        server_default="unmapped",
    )
