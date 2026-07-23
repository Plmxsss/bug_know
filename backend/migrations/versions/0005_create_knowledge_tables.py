"""Create knowledge document and RAG chunk tables.

Revision ID: 0005_knowledge_tables
Revises: 0004_pest_normalization
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_knowledge_tables"
down_revision: str | None = "0004_pest_normalization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create source provenance and chunk linkage tables."""

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("source_organization", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="uploaded",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'processing', 'indexed', 'failed')",
            name="ck_knowledge_documents_status",
        ),
        sa.CheckConstraint(
            "file_type IN ('pdf', 'txt', 'md')",
            name="ck_knowledge_documents_file_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checksum_sha256"),
    )
    op.create_table(
        "knowledge_document_entities",
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("pest_entity_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            name="fk_document_entities_document_id_knowledge_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pest_entity_id"],
            ["pest_entities.id"],
            name="fk_document_entities_entity_id_pest_entities",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("document_id", "pest_entity_id"),
    )
    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("pest_entity_id", sa.BigInteger(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("qdrant_point_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            name="fk_rag_chunks_document_id_knowledge_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pest_entity_id"],
            ["pest_entities.id"],
            name="fk_rag_chunks_entity_id_pest_entities",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "chunk_index >= 0",
            name="ck_rag_chunks_chunk_index",
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(content) > 0",
            name="ck_rag_chunks_content",
        ),
        sa.UniqueConstraint(
            "document_id",
            "pest_entity_id",
            "chunk_index",
            name="uq_rag_chunks_document_entity_index",
        ),
        sa.UniqueConstraint("qdrant_point_id"),
    )
    op.create_index(
        "ix_rag_chunks_pest_entity_id",
        "rag_chunks",
        ["pest_entity_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop knowledge tables in reverse dependency order."""

    op.drop_table("rag_chunks")
    op.drop_table("knowledge_document_entities")
    op.drop_table("knowledge_documents")
