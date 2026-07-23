"""Association between source documents and reviewed pest entities."""

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeDocumentEntity(Base):
    """Declare which entity metadata filters may use one document."""

    __tablename__ = "knowledge_document_entities"

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "knowledge_documents.id",
            name="fk_document_entities_document_id_knowledge_documents",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    pest_entity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "pest_entities.id",
            name="fk_document_entities_entity_id_pest_entities",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )
