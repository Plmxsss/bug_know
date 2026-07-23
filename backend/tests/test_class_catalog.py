"""Tests for dataset class loading and alias normalization."""

from pathlib import Path

import pytest

from app.services.class_catalog import load_yolo_class_catalog, normalize_alias


def test_normalize_alias_handles_width_case_and_spaces() -> None:
    """Equivalent user text should produce one stable alias key."""

    assert normalize_alias("  Ａphid   PEST ") == "aphid pest"


def test_load_catalog_accepts_contiguous_mapping(tmp_path: Path) -> None:
    """A valid YOLO mapping should preserve numeric order and Unicode labels."""

    path = tmp_path / "data.yaml"
    path.write_text("nc: 2\nnames:\n  0: 稻纵卷叶螟\n  1: 褐飞虱\n", encoding="utf-8")

    catalog = load_yolo_class_catalog(path)

    assert [item.class_id for item in catalog] == [0, 1]
    assert catalog[0].raw_class_name == "稻纵卷叶螟"


def test_load_catalog_rejects_missing_class_id(tmp_path: Path) -> None:
    """A gap would make model output IDs unsafe to map silently."""

    path = tmp_path / "data.yaml"
    path.write_text("nc: 2\nnames:\n  0: one\n  2: three\n", encoding="utf-8")

    with pytest.raises(ValueError, match="contiguous"):
        load_yolo_class_catalog(path)
