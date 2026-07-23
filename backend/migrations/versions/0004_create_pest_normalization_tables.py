"""Create pest entity normalization tables.

Revision ID: 0004_pest_normalization
Revises: 0003_detection_objects
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_pest_normalization"
down_revision: str | None = "0003_detection_objects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create normalized entities, aliases, and model-class mappings."""

    op.create_table(
        "pest_entities",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_code", sa.String(length=100), nullable=False),
        sa.Column("common_name", sa.String(length=200), nullable=False),
        sa.Column("scientific_name", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "knowledge_status",
            sa.String(length=20),
            server_default="missing",
            nullable=False,
        ),
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
            "knowledge_status IN ('missing', 'draft', 'reviewed')",
            name="ck_pest_entities_knowledge_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("common_name"),
        sa.UniqueConstraint("entity_code"),
    )
    op.create_table(
        "entity_aliases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("alias", sa.String(length=200), nullable=False),
        sa.Column("normalized_alias", sa.String(length=200), nullable=False),
        sa.Column(
            "language",
            sa.String(length=20),
            server_default="zh-CN",
            nullable=False,
        ),
        sa.Column(
            "alias_type",
            sa.String(length=30),
            server_default="common_name",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["pest_entities.id"],
            name="fk_entity_aliases_entity_id_pest_entities",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "normalized_alias",
            "language",
            name="uq_entity_aliases_normalized_language",
        ),
    )
    op.create_index(
        "ix_entity_aliases_entity_id",
        "entity_aliases",
        ["entity_id"],
        unique=False,
    )
    op.create_table(
        "model_class_mappings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("model_version_id", sa.BigInteger(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("raw_class_name", sa.String(length=200), nullable=False),
        sa.Column("pest_entity_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "mapping_status",
            sa.String(length=20),
            server_default="unmapped",
            nullable=False,
        ),
        sa.CheckConstraint(
            "class_id >= 0",
            name="ck_model_class_mappings_class_id",
        ),
        sa.CheckConstraint(
            "mapping_status IN ('unmapped', 'needs_review', 'verified')",
            name="ck_model_class_mappings_status",
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_versions.id"],
            name="fk_model_class_mappings_model_version_id_model_versions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pest_entity_id"],
            ["pest_entities.id"],
            name="fk_model_class_mappings_entity_id_pest_entities",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_version_id",
            "class_id",
            name="uq_model_class_mappings_model_class",
        ),
    )
    op.create_index(
        "ix_model_class_mappings_entity_id",
        "model_class_mappings",
        ["pest_entity_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop normalization tables in reverse dependency order."""

    op.drop_table("model_class_mappings")
    op.drop_table("entity_aliases")
    op.drop_table("pest_entities")
