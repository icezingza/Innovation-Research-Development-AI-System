"""Quota tracking and enforcement per tenant using Redis monthly counters."""

import calendar
import logging
from datetime import datetime, UTC

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Monthly API call limits per tier — adjust as business grows
TIER_LIMITS: dict[str, int] = {
    "free": 1_000,
    "pro": 50_000,
    "enterprise": 10_000_000,  # effectively unlimited
}
DEFAULT_LIMIT = TIER_LIMITS["free"]


class QuotaService:
    """Redis-backed monthly API call counter per tenant.

    Key pattern: quota:{tenant_id}:{YYYY-MM}
    TTL is set to the end of the current month so keys auto-expire.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    def _key(self, tenant_id: str) -> str:
        month = datetime.now(UTC).strftime("%Y-%m")
        return f"quota:{tenant_id}:{month}"

    def _month_ttl(self) -> int:
        """Seconds remaining until end of current UTC month."""
        now = datetime.now(UTC)
        last_day = calendar.monthrange(now.year, now.month)[1]
        end_of_month = now.replace(
            day=last_day, hour=23, minute=59, second=59, microsecond=0
        )
        return max(1, int((end_of_month - now).total_seconds()))

    async def increment(self, tenant_id: str) -> int:
        """Increment usage counter and return new total."""
        key = self._key(tenant_id)
        count = await self._redis.incr(key)
        if count == 1:
            # First call this month — set TTL to auto-expire at month end
            await self._redis.expire(key, self._month_ttl())
        return count

    async def current_usage(self, tenant_id: str) -> int:
        """Return current month usage without incrementing."""
        val = await self._redis.get(self._key(tenant_id))
        return int(val) if val else 0

    async def check_and_increment(
        self, tenant_id: str, tier: str
    ) -> tuple[bool, int, int]:
        """Atomically increment and check against quota limit.

        Returns:
            (allowed, current_usage, limit)
            allowed=False means the call should be rejected with 429.
        """
        limit = TIER_LIMITS.get(tier, DEFAULT_LIMIT)
        usage = await self.increment(tenant_id)
        allowed = usage <= limit
        if not allowed:
            logger.warning(
                "quota_exceeded",
                extra={
                    "tenant_id": tenant_id,
                    "tier": tier,
                    "usage": usage,
                    "limit": limit,
                },
            )
        return allowed, usage, limit
