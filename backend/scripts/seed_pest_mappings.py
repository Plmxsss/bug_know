"""Seed all YOLO classes as unreviewed normalized pest mappings."""

import argparse
import asyncio
from pathlib import Path

from app.core.config import PROJECT_ROOT, get_settings
from app.db.session import Database
from app.repositories import ModelVersionRepository
from app.services import PestMappingSeedService
from app.services.class_catalog import load_yolo_class_catalog


def parse_args() -> argparse.Namespace:
    """Read model identity and dataset YAML arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="ip102-yolo26n")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument(
        "--data-yaml",
        type=Path,
        default=PROJECT_ROOT / "data" / "data.yaml",
    )
    return parser.parse_args()


async def seed(args: argparse.Namespace) -> None:
    """Run one transactional, repeatable catalog import."""

    catalog = load_yolo_class_catalog(args.data_yaml.resolve())
    database = Database(get_settings())
    try:
        async with database.session_factory() as session:
            async with session.begin():
                model = await ModelVersionRepository(
                    session
                ).get_by_name_and_version(
                    name=args.name,
                    version=args.version,
                )
                if model is None:
                    raise RuntimeError(
                        f"Model version {args.name}:{args.version} is not registered."
                    )
                summary = await PestMappingSeedService(session).seed(
                    model_version_id=model.id,
                    catalog=catalog,
                )
        print(
            {
                "model_version_id": model.id,
                "classes_seen": summary.classes_seen,
                "entities_created": summary.entities_created,
                "aliases_created": summary.aliases_created,
                "mappings_created": summary.mappings_created,
                "mappings_updated": summary.mappings_updated,
            }
        )
    finally:
        await database.close()


def main() -> None:
    """Program entry point."""

    asyncio.run(seed(parse_args()))


if __name__ == "__main__":
    main()
