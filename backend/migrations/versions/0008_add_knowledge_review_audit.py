"""Add audit fields for pest knowledge reviews.

Revision ID: 0008_knowledge_review_audit
Revises: 0007_mapping_review_audit
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_knowledge_review_audit"
down_revision: str | None = "0007_mapping_review_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record who approved an entity's knowledge, when, and why."""

    op.add_column(
        "pest_entities",
        sa.Column(
            "knowledge_reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "pest_entities",
        sa.Column(
            "knowledge_reviewed_by",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "pest_entities",
        sa.Column("knowledge_review_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove knowledge review audit fields."""

    op.drop_column("pest_entities", "knowledge_review_note")
    op.drop_column("pest_entities", "knowledge_reviewed_by")
    op.drop_column("pest_entities", "knowledge_reviewed_at")
