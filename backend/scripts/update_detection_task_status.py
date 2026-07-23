"""Move a detection task through one valid processing state transition."""

import argparse
import asyncio
import json

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.session import Database
from app.services import DetectionTaskService


def build_parser() -> argparse.ArgumentParser:
    """Define valid status transition commands and their required values."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=int, required=True)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("start")

    complete_parser = actions.add_parser("complete")
    complete_parser.add_argument("--annotated-image-path", required=True)

    fail_parser = actions.add_parser("fail")
    fail_parser.add_argument("--error-message", required=True)
    return parser


async def update_status(args: argparse.Namespace) -> None:
    """Apply one state transition and print the updated task."""

    database = Database(get_settings())
    try:
        async with database.session_factory() as session:
            service = DetectionTaskService(session)
            if args.action == "start":
                task = await service.start(args.task_id)
            elif args.action == "complete":
                task = await service.complete(
                    args.task_id,
                    annotated_image_path=args.annotated_image_path,
                )
            else:
                task = await service.fail(
                    args.task_id,
                    error_message=args.error_message,
                )

            print(
                json.dumps(
                    {
                        "id": task.id,
                        "status": task.status,
                        "annotated_image_path": task.annotated_image_path,
                        "error_message": task.error_message,
                        "completed_at": (
                            task.completed_at.isoformat()
                            if task.completed_at is not None
                            else None
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
    finally:
        await database.close()


def main() -> None:
    """Parse the command and report business errors without a traceback."""

    parser = build_parser()
    try:
        asyncio.run(update_status(parser.parse_args()))
    except AppError as exc:
        parser.error(exc.message)


if __name__ == "__main__":
    main()
