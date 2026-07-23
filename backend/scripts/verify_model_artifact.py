"""Verify model and regression files against a committed manifest."""

import argparse
import hashlib
import json
from pathlib import Path

from app.core.config import PROJECT_ROOT


def calculate_sha256(file_path: Path) -> str:
    """Calculate a file fingerprint without loading the full file at once."""

    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(*, path: Path, size_bytes: int, sha256: str) -> list[str]:
    """Return human-readable problems found for one expected file."""

    if not path.is_file():
        return [f"Missing file: {path}"]

    problems = []
    actual_size = path.stat().st_size
    if actual_size != size_bytes:
        problems.append(
            f"Size mismatch for {path}: expected {size_bytes}, got {actual_size}"
        )

    actual_hash = calculate_sha256(path)
    if actual_hash != sha256:
        problems.append(
            f"SHA-256 mismatch for {path}: expected {sha256}, got {actual_hash}"
        )
    return problems


def verify_manifest(manifest_path: Path) -> list[str]:
    """Verify every local file described by one model manifest."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    model = manifest["model"]
    problems = verify_file(
        path=PROJECT_ROOT / model["weights_path"],
        size_bytes=model["weights_size_bytes"],
        sha256=model["weights_sha256"],
    )

    for image in manifest["smoke_regression_images"]:
        problems.extend(
            verify_file(
                path=PROJECT_ROOT / image["path"],
                size_bytes=image["size_bytes"],
                sha256=image["sha256"],
            )
        )
    return problems


def build_parser() -> argparse.ArgumentParser:
    """Define the optional manifest location."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT
        / "model_artifacts"
        / "ip102-yolo26n"
        / "manifest.json",
    )
    return parser


def main() -> None:
    """Run verification and return a failing exit code for any mismatch."""

    args = build_parser().parse_args()
    problems = verify_manifest(args.manifest.resolve())
    if problems:
        raise SystemExit("\n".join(problems))
    print("Model artifact verification passed.")


if __name__ == "__main__":
    main()
