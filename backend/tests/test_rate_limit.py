"""Tests for Redis-backed expensive-request limits."""

import pytest

from app.core.exceptions import AppError
from app.services.rate_limit import FixedWindowRateLimiter


class FakeCounter:
    """Return a configured atomic counter or simulate Redis failure."""

    def __init__(self, count: int = 1, *, fail: bool = False) -> None:
        self.count = count
        self.fail = fail
        self.calls: list[tuple[str, int]] = []

    async def increment_with_expiry(
        self,
        *,
        key: str,
        ttl_seconds: int,
    ) -> int:
        self.calls.append((key, ttl_seconds))
        if self.fail:
            raise ConnectionError("secret Redis endpoint")
        return self.count

    async def ping(self) -> None:
        return None

    async def close(self) -> None:
        return None


async def test_rate_limit_allows_request_with_remaining_capacity() -> None:
    """A count under the limit should report remaining requests."""

    redis = FakeCounter(count=3)
    decision = await FixedWindowRateLimiter(redis).check(
        key="rate:test",
        limit=5,
        window_seconds=60,
    )

    assert decision.allowed is True
    assert decision.remaining == 2
    assert redis.calls == [("rate:test", 60)]


async def test_rate_limit_rejects_count_over_limit() -> None:
    """The first count over the configured maximum should be denied."""

    decision = await FixedWindowRateLimiter(FakeCounter(count=6)).check(
        key="rate:test",
        limit=5,
        window_seconds=60,
    )

    assert decision.allowed is False
    assert decision.remaining == 0


async def test_rate_limit_fails_closed_without_leaking_redis_details() -> None:
    """Redis failure must not allow an expensive model request through."""

    with pytest.raises(AppError) as exc_info:
        await FixedWindowRateLimiter(FakeCounter(fail=True)).check(
            key="rate:test",
            limit=5,
            window_seconds=60,
        )

    assert exc_info.value.code == "RATE_LIMIT_STORE_UNAVAILABLE"
    assert "secret Redis endpoint" not in exc_info.value.message
