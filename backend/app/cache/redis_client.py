"""Application-lifetime asynchronous Redis connection."""

from typing import Protocol

from redis.asyncio import Redis

from app.core.config import Settings


class RedisGateway(Protocol):
    """Small Redis behavior required by lifecycle and readiness."""

    async def ping(self) -> None:
        """Raise when Redis cannot answer."""

    async def close(self) -> None:
        """Release pooled Redis connections."""


class RedisClient:
    """Share one concurrency-safe redis-py client across API requests."""

    def __init__(self, settings: Settings) -> None:
        password = settings.redis_password.get_secret_value() or None
        self._client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_database,
            password=password,
            decode_responses=True,
            max_connections=settings.redis_max_connections,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )

    async def ping(self) -> None:
        """Verify authentication and a minimal Redis round trip."""

        response = await self._client.ping()
        if response is not True:
            raise ConnectionError("Redis PING did not return true.")

    async def close(self) -> None:
        """Close the client and its owned connection pool."""

        await self._client.aclose()
