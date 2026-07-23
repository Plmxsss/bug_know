"""Load and validate class IDs and labels from a YOLO dataset file."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unicodedata import normalize

import yaml


@dataclass(frozen=True, slots=True)
class ModelClass:
    """One class ID and raw name from a training dataset configuration."""

    class_id: int
    raw_class_name: str


def normalize_alias(value: str) -> str:
    """Create a stable lookup form without changing the displayed alias."""

    normalized = normalize("NFKC", value)
    return " ".join(normalized.casefold().split())


def load_yolo_class_catalog(path: Path) -> tuple[ModelClass, ...]:
    """Read a YOLO YAML file and require contiguous IDs matching ``nc``."""

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("The dataset YAML root must be a mapping.")

    raw_count = data.get("nc")
    raw_names = data.get("names")
    if not isinstance(raw_count, int) or raw_count <= 0:
        raise ValueError("The dataset YAML requires a positive integer nc.")

    indexed_names: list[tuple[int, Any]]
    if isinstance(raw_names, list):
        indexed_names = list(enumerate(raw_names))
    elif isinstance(raw_names, dict):
        try:
            indexed_names = sorted(
                (int(class_id), name) for class_id, name in raw_names.items()
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Every class ID must be an integer.") from exc
    else:
        raise ValueError("The dataset YAML names must be a list or mapping.")

    expected_ids = list(range(raw_count))
    actual_ids = [class_id for class_id, _name in indexed_names]
    if actual_ids != expected_ids:
        raise ValueError("Class IDs must be contiguous from 0 through nc - 1.")

    catalog: list[ModelClass] = []
    for class_id, raw_name in indexed_names:
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError(f"Class {class_id} requires a non-empty string name.")
        catalog.append(
            ModelClass(
                class_id=class_id,
                raw_class_name=raw_name.strip(),
            )
        )
    return tuple(catalog)
