"""Tests for the model_versions ORM table definition."""

from sqlalchemy import UniqueConstraint

from app.db.base import Base
from app.models import ModelVersion


def test_model_version_is_registered_as_a_table() -> None:
    """Importing the model should register its table and expected columns."""

    table = Base.metadata.tables["model_versions"]

    assert ModelVersion.__table__ is table
    assert set(table.columns.keys()) == {
        "id",
        "name",
        "version",
        "weights_path",
        "checksum_sha256",
        "class_count",
        "is_active",
        "created_at",
    }
    assert table.primary_key.columns.keys() == ["id"]


def test_name_and_version_must_be_unique_together() -> None:
    """The same named model version should not be registered twice."""

    constraints = ModelVersion.__table__.constraints
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("name", "version") in unique_columns


def test_model_version_can_be_created_as_a_python_object() -> None:
    """An ORM row begins as an ordinary Python object before persistence."""

    model = ModelVersion(
        name="ip102-yolo",
        version="1.0.0",
        weights_path="models/ip102/best.pt",
        checksum_sha256="a" * 64,
        class_count=102,
        is_active=True,
    )

    assert model.name == "ip102-yolo"
    assert model.class_count == 102
    assert model.is_active is True
