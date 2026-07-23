"""Create diagnosis report lifecycle and result table.

Revision ID: 0009_diagnosis_reports
Revises: 0008_knowledge_review_audit
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_diagnosis_reports"
down_revision: str | None = "0008_knowledge_review_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create one idempotent report row per detection task."""

    op.create_table(
        "diagnosis_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="processing",
            nullable=False,
        ),
        sa.Column("llm_provider", sa.String(length=100), nullable=True),
        sa.Column("llm_model", sa.String(length=200), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="ck_diagnosis_reports_status",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["detection_tasks.id"],
            name="fk_diagnosis_reports_task_id_detection_tasks",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            name="uq_diagnosis_reports_task_id",
        ),
    )


def downgrade() -> None:
    """Drop diagnosis report persistence."""

    op.drop_table("diagnosis_reports")
