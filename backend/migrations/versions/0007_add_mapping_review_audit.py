"""Add audit fields for model-class mapping reviews.

Revision ID: 0007_mapping_review_audit
Revises: 0006_rag_chunk_locator
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_mapping_review_audit"
down_revision: str | None = "0006_rag_chunk_locator"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record who verified a mapping, when, and why."""

    op.add_column(
        "model_class_mappings",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "model_class_mappings",
        sa.Column("verified_by", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "model_class_mappings",
        sa.Column("review_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove mapping review audit fields."""

    op.drop_column("model_class_mappings", "review_note")
    op.drop_column("model_class_mappings", "verified_by")
    op.drop_column("model_class_mappings", "verified_at")
