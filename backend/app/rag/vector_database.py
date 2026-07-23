"""Create and manage the asynchronous Qdrant client."""

from dataclasses import dataclass
from typing import Any, Protocol, cast

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class VectorPoint:
    """Framework-independent point prepared by the indexing service."""

    point_id: str
    vector: list[float]
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class VectorSearchHit:
    """Minimal search result independent of Qdrant response classes."""

    point_id: str
    score: float


class VectorDatabaseGateway(Protocol):
    """Small Qdrant behavior required by application lifecycle and readiness."""

    async def ping(self) -> None:
        """Raise an exception when Qdrant cannot answer."""

    async def close(self) -> None:
        """Release network resources owned by the client."""

    async def ensure_collection(
        self,
        *,
        collection_name: str,
        dimension: int,
    ) -> None:
        """Create or validate one cosine-distance collection."""

    async def upsert_points(
        self,
        *,
        collection_name: str,
        points: list[VectorPoint],
    ) -> None:
        """Insert or replace deterministic vector points."""

    async def search_by_entity(
        self,
        *,
        collection_name: str,
        query_vector: list[float],
        pest_entity_id: int,
        limit: int,
    ) -> list[VectorSearchHit]:
        """Search only points whose payload belongs to one pest entity."""


class QdrantVectorDatabase:
    """Own one shared async client for Qdrant operations."""

    def __init__(self, settings: Settings) -> None:
        self.client = AsyncQdrantClient(url=settings.qdrant_url)

    async def ping(self) -> None:
        """Request collection metadata as a minimal connectivity check."""

        await self.client.get_collections()

    async def close(self) -> None:
        """Close the underlying HTTP and optional gRPC clients."""

        await self.client.close()

    async def ensure_collection(
        self,
        *,
        collection_name: str,
        dimension: int,
    ) -> None:
        """Create a cosine collection or reject an incompatible existing one."""

        if not await self.client.collection_exists(collection_name):
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,
                ),
            )
            return

        info = await self.client.get_collection(collection_name)
        vectors_config = cast(Any, info.config.params.vectors)
        actual_size = getattr(vectors_config, "size", None)
        actual_distance = getattr(vectors_config, "distance", None)
        if actual_size != dimension or actual_distance != Distance.COSINE:
            raise ValueError(
                f"Qdrant collection {collection_name!r} has incompatible "
                f"vector settings: size={actual_size}, distance={actual_distance}."
            )

    async def upsert_points(
        self,
        *,
        collection_name: str,
        points: list[VectorPoint],
    ) -> None:
        """Upsert points and wait until they are available for retrieval."""

        if not points:
            return
        await self.client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=point.point_id,
                    vector=point.vector,
                    payload=point.payload,
                )
                for point in points
            ],
            wait=True,
        )

    async def search_by_entity(
        self,
        *,
        collection_name: str,
        query_vector: list[float],
        pest_entity_id: int,
        limit: int,
    ) -> list[VectorSearchHit]:
        """Run cosine search with a mandatory exact entity payload filter."""

        response = await self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="pest_entity_id",
                        match=MatchValue(value=pest_entity_id),
                    )
                ]
            ),
            with_payload=False,
            limit=limit,
        )
        return [
            VectorSearchHit(point_id=str(point.id), score=float(point.score))
            for point in response.points
        ]
