"""Review one pest entity's indexed knowledge and provenance."""

import argparse
import asyncio

from app.core.config import get_settings
from app.db.session import Database
from app.services import KnowledgeReviewService


def parse_args() -> argparse.Namespace:
    """Require an entity assertion plus honest reviewer audit fields."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entity-code", required=True)
    parser.add_argument("--expected-common-name", required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--note", required=True)
    return parser.parse_args()


async def review(args: argparse.Namespace) -> None:
    """Commit review state only when all source prerequisites pass."""

    database = Database(get_settings())
    try:
        async with database.session_factory() as session:
            async with session.begin():
                result = await KnowledgeReviewService(session).review(
                    entity_code=args.entity_code,
                    expected_common_name=args.expected_common_name,
                    reviewed_by=args.reviewed_by,
                    review_note=args.note,
                )
        print(
            {
                "entity_id": result.entity_id,
                "entity_code": result.entity_code,
                "common_name": result.common_name,
                "document_ids": result.document_ids,
                "source_organizations": result.source_organizations,
                "reviewed_at": result.reviewed_at.isoformat(),
            }
        )
    finally:
        await database.close()


def main() -> None:
    """Program entry point."""

    asyncio.run(review(parse_args()))


if __name__ == "__main__":
    main()
