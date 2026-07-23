"""Create the detection_tasks table.

Revision ID: 0002_detection_tasks
Revises: 0001_model_versions
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_detection_tasks"
down_revision: str | None = "0001_model_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the table when moving the database forward."""

    op.create_table(
        "detection_tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("model_version_id", sa.BigInteger(), nullable=False),
        sa.Column("original_image_path", sa.String(length=500), nullable=False),
        sa.Column("annotated_image_path", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_detection_tasks_status",
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_versions.id"],
            name="fk_detection_tasks_model_version_id_model_versions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_detection_tasks_model_version_id",
        "detection_tasks",
        ["model_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_detection_tasks_status_created_at",
        "detection_tasks",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the table when moving the database backward."""

    op.drop_table("detection_tasks")
