"""Application-lifetime asynchronous Redis connection."""

from collections.abc import Awaitable
from typing import Protocol, cast

from redis.asyncio import Redis

from app.core.config import Settings


class RedisGateway(Protocol):
    """Small Redis behavior required by lifecycle and readiness."""

    async def ping(self) -> None:
        """Raise when Redis cannot answer."""

    async def close(self) -> None:
        """Release pooled Redis connections."""

    async def increment_with_expiry(
        self,
        *,
        key: str,
        ttl_seconds: int,
    ) -> int:
        """Atomically increment a counter and set TTL on first use."""


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

    async def increment_with_expiry(
        self,
        *,
        key: str,
        ttl_seconds: int,
    ) -> int:
        """Use one Lua script so INCR and initial EXPIRE cannot separate."""

        script = """
        local current = redis.call('INCR', KEYS[1])
        if current == 1 then
            redis.call('EXPIRE', KEYS[1], ARGV[1])
        end
        return current
        """
        result = await cast(
            Awaitable[object],
            self._client.eval(
                script,
                1,
                key,
                str(ttl_seconds),
            ),
        )
        if not isinstance(result, int) or isinstance(result, bool):
            raise RuntimeError("Redis rate-limit script returned a non-integer.")
        return result
