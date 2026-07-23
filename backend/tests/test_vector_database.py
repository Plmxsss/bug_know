"""Tests for Qdrant collection validation and point conversion."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from qdrant_client.models import Distance, MatchValue, PointStruct

from app.core.config import Settings
from app.rag.vector_database import QdrantVectorDatabase, VectorPoint


def _database() -> QdrantVectorDatabase:
    database = QdrantVectorDatabase(Settings(_env_file=None))
    database.client = AsyncMock()
    return database


async def test_missing_collection_is_created_for_cosine_vectors() -> None:
    """The configured embedding dimension should define a new collection."""

    database = _database()
    database.client.collection_exists.return_value = False

    await database.ensure_collection(
        collection_name="knowledge",
        dimension=512,
    )

    database.client.create_collection.assert_awaited_once()
    options = database.client.create_collection.await_args.kwargs
    assert options["collection_name"] == "knowledge"
    assert options["vectors_config"].size == 512
    assert options["vectors_config"].distance == Distance.COSINE


async def test_existing_collection_dimension_mismatch_is_rejected() -> None:
    """Changing embedding models requires a new compatible collection."""

    database = _database()
    database.client.collection_exists.return_value = True
    database.client.get_collection.return_value = SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(
                vectors=SimpleNamespace(size=768, distance=Distance.COSINE)
            )
        )
    )

    with pytest.raises(ValueError, match="size=768"):
        await database.ensure_collection(
            collection_name="knowledge",
            dimension=512,
        )


async def test_upsert_converts_project_points_and_waits() -> None:
    """Indexing should not report success before Qdrant applies the write."""

    database = _database()
    point = VectorPoint(
        point_id="97c65d7e-2c2e-4da8-b96f-82d0023bbce2",
        vector=[1.0, 0.0],
        payload={"pest_entity_id": 1},
    )

    await database.upsert_points(
        collection_name="knowledge",
        points=[point],
    )

    options = database.client.upsert.await_args.kwargs
    assert options["wait"] is True
    assert options["points"] == [
        PointStruct(
            id=point.point_id,
            vector=point.vector,
            payload=point.payload,
        )
    ]


async def test_search_requires_exact_pest_entity_filter() -> None:
    """Similarity search must never span every pest's knowledge."""

    database = _database()
    database.client.query_points.return_value = SimpleNamespace(
        points=[
            SimpleNamespace(
                id="97c65d7e-2c2e-4da8-b96f-82d0023bbce2",
                score=0.88,
            )
        ]
    )

    hits = await database.search_by_entity(
        collection_name="knowledge",
        query_vector=[1.0, 0.0],
        pest_entity_id=7,
        limit=3,
    )

    options = database.client.query_points.await_args.kwargs
    condition = options["query_filter"].must[0]
    assert condition.key == "pest_entity_id"
    assert condition.match == MatchValue(value=7)
    assert options["with_payload"] is False
    assert hits[0].score == pytest.approx(0.88)
