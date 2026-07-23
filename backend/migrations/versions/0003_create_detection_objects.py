"""Create the detection_objects table.

Revision ID: 0003_detection_objects
Revises: 0002_detection_tasks
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_detection_objects"
down_revision: str | None = "0002_detection_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the table when moving the database forward."""

    op.create_table(
        "detection_objects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("raw_class_name", sa.String(length=200), nullable=False),
        sa.Column("normalized_entity_id", sa.BigInteger(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bbox_x1", sa.Float(), nullable=False),
        sa.Column("bbox_y1", sa.Float(), nullable=False),
        sa.Column("bbox_x2", sa.Float(), nullable=False),
        sa.Column("bbox_y2", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_detection_objects_confidence",
        ),
        sa.CheckConstraint(
            "bbox_x1 >= 0 AND bbox_y1 >= 0 "
            "AND bbox_x2 > bbox_x1 AND bbox_y2 > bbox_y1",
            name="ck_detection_objects_bbox",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["detection_tasks.id"],
            name="fk_detection_objects_task_id_detection_tasks",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_detection_objects_task_id",
        "detection_objects",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "ix_detection_objects_normalized_entity_id",
        "detection_objects",
        ["normalized_entity_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the table when moving the database backward."""

    op.drop_table("detection_objects")
