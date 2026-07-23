"""Create one pending detection task for an existing local image."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.core.config import PROJECT_ROOT, get_settings
from app.db.session import Database
from app.repositories import DetectionTaskRepository


def build_parser() -> argparse.ArgumentParser:
    """Define the values required by the task creation command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-version-id", type=int, required=True)
    parser.add_argument("--image-path", type=Path, required=True)
    return parser


async def create_task(args: argparse.Namespace) -> None:
    """Create one task and print its stored database values."""

    absolute_path = args.image_path.resolve()
    if not absolute_path.is_file():
        raise FileNotFoundError(f"Image does not exist: {absolute_path}")

    try:
        stored_path = absolute_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        stored_path = absolute_path.as_posix()

    database = Database(get_settings())
    try:
        async with database.session_factory() as session:
            repository = DetectionTaskRepository(session)
            try:
                async with session.begin():
                    task = await repository.create(
                        model_version_id=args.model_version_id,
                        original_image_path=stored_path,
                    )
            except IntegrityError as exc:
                raise ValueError(
                    f"Model version {args.model_version_id} does not exist."
                ) from exc

            print(
                json.dumps(
                    {
                        "id": task.id,
                        "model_version_id": task.model_version_id,
                        "original_image_path": task.original_image_path,
                        "status": task.status,
                        "created_at": task.created_at.isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
    finally:
        await database.close()


def main() -> None:
    """Parse command-line values and run asynchronous task creation."""

    parser = build_parser()
    try:
        asyncio.run(create_task(parser.parse_args()))
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
