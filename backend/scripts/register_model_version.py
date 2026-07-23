"""Register one local model artifact in the model_versions table."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from app.core.config import PROJECT_ROOT, get_settings
from app.db.session import Database
from app.repositories import ModelVersionRepository


def calculate_sha256(file_path: Path) -> str:
    """Calculate a stable fingerprint without loading the whole file into memory."""

    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    """Define the values required by the registration command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--weights-path", type=Path, required=True)
    parser.add_argument("--class-count", type=int, required=True)
    parser.add_argument("--active", action="store_true")
    return parser


async def register_model(args: argparse.Namespace) -> None:
    """Insert the model when absent and print the stored database row."""

    absolute_path = args.weights_path.resolve()
    if not absolute_path.is_file():
        raise FileNotFoundError(f"Model weights do not exist: {absolute_path}")

    try:
        stored_path = absolute_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        stored_path = absolute_path.as_posix()

    database = Database(get_settings())
    try:
        async with database.session_factory() as session:
            repository = ModelVersionRepository(session)
            async with session.begin():
                model_version = await repository.get_by_name_and_version(
                    name=args.name,
                    version=args.version,
                )
                created = model_version is None
                if model_version is None:
                    model_version = await repository.create(
                        name=args.name,
                        version=args.version,
                        weights_path=stored_path,
                        checksum_sha256=calculate_sha256(absolute_path),
                        class_count=args.class_count,
                        is_active=args.active,
                    )

            print(
                json.dumps(
                    {
                        "created": created,
                        "id": model_version.id,
                        "name": model_version.name,
                        "version": model_version.version,
                        "weights_path": model_version.weights_path,
                        "checksum_sha256": model_version.checksum_sha256,
                        "class_count": model_version.class_count,
                        "is_active": model_version.is_active,
                        "created_at": model_version.created_at.isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
    finally:
        await database.close()


def main() -> None:
    """Parse command-line values and run the asynchronous registration."""

    asyncio.run(register_model(build_parser().parse_args()))


if __name__ == "__main__":
    main()
