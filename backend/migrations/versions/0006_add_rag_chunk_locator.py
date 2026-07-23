"""Add citation locator to RAG chunks.

Revision ID: 0006_rag_chunk_locator
Revises: 0005_knowledge_tables
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_rag_chunk_locator"
down_revision: str | None = "0005_knowledge_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store page or heading locators for citation reconstruction."""

    op.add_column(
        "rag_chunks",
        sa.Column(
            "locator",
            sa.String(length=500),
            server_default="document",
            nullable=False,
        ),
    )
    op.alter_column(
        "rag_chunks",
        "locator",
        server_default=None,
        existing_type=sa.String(length=500),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Remove citation locators."""

    op.drop_column("rag_chunks", "locator")
