"""Redis-backed fixed-window decisions for expensive endpoints."""

from dataclasses import dataclass

from fastapi import status

from app.cache import RedisGateway
from app.core.exceptions import AppError


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Counter result with values safe to expose in response metadata."""

    allowed: bool
    limit: int
    count: int
    remaining: int
    window_seconds: int


class FixedWindowRateLimiter:
    """Count a key within one Redis TTL window."""

    def __init__(self, redis: RedisGateway) -> None:
        self._redis = redis

    async def check(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitDecision:
        """Return a decision or fail closed when Redis is unavailable."""

        try:
            count = await self._redis.increment_with_expiry(
                key=key,
                ttl_seconds=window_seconds,
            )
        except Exception as exc:
            raise AppError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="RATE_LIMIT_STORE_UNAVAILABLE",
                message="The request limit store is currently unavailable.",
            ) from exc
        return RateLimitDecision(
            allowed=count <= limit,
            limit=limit,
            count=count,
            remaining=max(limit - count, 0),
            window_seconds=window_seconds,
        )
