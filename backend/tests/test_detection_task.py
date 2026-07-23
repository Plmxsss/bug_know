"""Tests for the detection_tasks ORM table definition."""

from sqlalchemy import CheckConstraint

from app.db.base import Base
from app.models import DetectionTask


def test_detection_task_is_registered_with_expected_columns() -> None:
    """The ORM model should register the complete first task table."""

    table = Base.metadata.tables["detection_tasks"]

    assert DetectionTask.__table__ is table
    assert set(table.columns.keys()) == {
        "id",
        "model_version_id",
        "original_image_path",
        "annotated_image_path",
        "status",
        "error_message",
        "created_at",
        "completed_at",
    }
    assert table.primary_key.columns.keys() == ["id"]


def test_detection_task_references_model_version() -> None:
    """Every task should point to a registered model version row."""

    foreign_key = next(iter(DetectionTask.__table__.c.model_version_id.foreign_keys))

    assert foreign_key.target_fullname == "model_versions.id"
    assert foreign_key.ondelete == "RESTRICT"


def test_detection_status_is_limited_to_known_values() -> None:
    """The database definition should reject unknown task statuses."""

    check_constraints = {
        constraint.name
        for constraint in DetectionTask.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_detection_tasks_status" in check_constraints


def test_unfinished_detection_task_allows_missing_output_values() -> None:
    """A newly created task has no annotated image, error, or completion time."""

    task = DetectionTask(
        model_version_id=1,
        original_image_path="uploads/original/example.jpg",
        annotated_image_path=None,
        status="pending",
        error_message=None,
        completed_at=None,
    )

    assert task.model_version_id == 1
    assert task.status == "pending"
    assert task.annotated_image_path is None
    assert task.completed_at is None
