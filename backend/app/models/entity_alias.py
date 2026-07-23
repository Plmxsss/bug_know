"""ORM model for searchable names belonging to normalized pest entities."""

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EntityAlias(Base):
    """Map one normalized text alias to a pest entity."""

    __tablename__ = "entity_aliases"
    __table_args__ = (
        UniqueConstraint(
            "normalized_alias",
            "language",
            name="uq_entity_aliases_normalized_language",
        ),
        Index("ix_entity_aliases_entity_id", "entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "pest_entities.id",
            name="fk_entity_aliases_entity_id_pest_entities",
            ondelete="CASCADE",
        ),
    )
    alias: Mapped[str] = mapped_column(String(200))
    normalized_alias: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(
        String(20),
        default="zh-CN",
        server_default="zh-CN",
    )
    alias_type: Mapped[str] = mapped_column(
        String(30),
        default="common_name",
        server_default="common_name",
    )
