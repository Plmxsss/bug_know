"""Verify one exact model class to pest entity mapping."""

import argparse
import asyncio

from app.core.config import get_settings
from app.db.session import Database
from app.services import PestMappingReviewService


def parse_args() -> argparse.Namespace:
    """Require explicit identity assertions and audit information."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="ip102-yolo26n")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--class-id", type=int, required=True)
    parser.add_argument("--expected-label", required=True)
    parser.add_argument("--expected-entity-code", required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--note", required=True)
    return parser.parse_args()


async def review(args: argparse.Namespace) -> None:
    """Commit one review only after every supplied assertion matches."""

    database = Database(get_settings())
    try:
        async with database.session_factory() as session:
            async with session.begin():
                result = await PestMappingReviewService(session).verify(
                    model_name=args.name,
                    model_version=args.version,
                    class_id=args.class_id,
                    expected_raw_class_name=args.expected_label,
                    expected_entity_code=args.expected_entity_code,
                    verified_by=args.reviewed_by,
                    review_note=args.note,
                )
        print(
            {
                "model_version_id": result.model_version_id,
                "class_id": result.class_id,
                "raw_class_name": result.raw_class_name,
                "entity_id": result.entity_id,
                "entity_code": result.entity_code,
                "common_name": result.common_name,
                "verified_at": result.verified_at.isoformat(),
            }
        )
    finally:
        await database.close()


def main() -> None:
    """Program entry point."""

    asyncio.run(review(parse_args()))


if __name__ == "__main__":
    main()
