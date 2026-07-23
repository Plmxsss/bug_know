"""ORM model linking retrievable text chunks to Qdrant points."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RagChunk(Base):
    """Keep source text and vector identity available for citation checks."""

    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "pest_entity_id",
            "chunk_index",
            name="uq_rag_chunks_document_entity_index",
        ),
        Index("ix_rag_chunks_pest_entity_id", "pest_entity_id"),
        CheckConstraint("chunk_index >= 0", name="ck_rag_chunks_chunk_index"),
        CheckConstraint(
            "CHAR_LENGTH(content) > 0",
            name="ck_rag_chunks_content",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "knowledge_documents.id",
            name="fk_rag_chunks_document_id_knowledge_documents",
            ondelete="CASCADE",
        ),
    )
    pest_entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "pest_entities.id",
            name="fk_rag_chunks_entity_id_pest_entities",
            ondelete="RESTRICT",
        ),
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(500))
    locator: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(String(64))
    qdrant_point_id: Mapped[str] = mapped_column(String(36), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
