"""Create and manage the asynchronous Qdrant client."""

from typing import Protocol

from qdrant_client import AsyncQdrantClient

from app.core.config import Settings


class VectorDatabaseGateway(Protocol):
    """Small Qdrant behavior required by application lifecycle and readiness."""

    async def ping(self) -> None:
        """Raise an exception when Qdrant cannot answer."""

    async def close(self) -> None:
        """Release network resources owned by the client."""


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
