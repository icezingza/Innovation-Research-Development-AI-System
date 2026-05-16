"""Redis-backed sliding-window rate limiter, per-tenant, tier-aware.

Algorithm: Redis Sorted Set where each member is a unique request ID
and each score is the Unix timestamp (ms). A Lua script atomically:
  1. Removes entries older than the window
  2. Counts remaining entries
  3. Rejects if count >= limit, otherwise adds the new entry + sets TTL

This is race-condition-free even across multiple API worker processes.
"""
import logging
import time
import uuid

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Requests-per-minute limits per tier
TIER_RATE_LIMITS: dict[str, int] = {
    "free": 30,
    "pro": 300,
    "enterprise": 1_000,
}
DEFAULT_RATE_LIMIT = TIER_RATE_LIMITS["free"]

# Sliding window duration in milliseconds
WINDOW_MS = 60_000  # 1 minute

# Lua script: atomic sliding-window check-and-add
# KEYS[1] = sorted-set key
# ARGV[1] = now_ms (current timestamp in ms)
# ARGV[2] = window_start_ms (now_ms - WINDOW_MS)
# ARGV[3] = limit (max requests per window)
# ARGV[4] = member (unique request ID)
# ARGV[5] = ttl_seconds (key expiry)
# Returns: current count AFTER adding (if allowed), or -1 if rejected
_SLIDING_WINDOW_LUA = """
local key       = KEYS[1]
local now       = tonumber(ARGV[1])
local win_start = tonumber(ARGV[2])
local limit     = tonumber(ARGV[3])
local member    = ARGV[4]
local ttl       = tonumber(ARGV[5])

redis.call('ZREMRANGEBYSCORE', key, '-inf', win_start)
local count = redis.call('ZCARD', key)

if count >= limit then
    return -1
end

redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, ttl)
return count + 1
"""


class RedisRateLimiter:
    """Sliding-window rate limiter backed by Redis Sorted Sets.

    Key pattern: ratelimit:{identifier}  (identifier = tenant_id or IP)
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._script = redis_client.register_script(_SLIDING_WINDOW_LUA)

    def _key(self, identifier: str) -> str:
        return f"ratelimit:{identifier}"

    async def is_allowed(self, identifier: str, tier: str) -> tuple[bool, int, int]:
        """Check and register a request against the sliding window.

        Returns:
            (allowed, current_count, limit)
        """
        limit = TIER_RATE_LIMITS.get(tier, DEFAULT_RATE_LIMIT)
        now_ms = int(time.time() * 1000)
        win_start_ms = now_ms - WINDOW_MS
        member = str(uuid.uuid4())
        ttl_seconds = (WINDOW_MS // 1000) + 5  # small buffer after window closes

        result = await self._script(
            keys=[self._key(identifier)],
            args=[now_ms, win_start_ms, limit, member, ttl_seconds],
        )

        if result == -1:
            current = await self._redis.zcard(self._key(identifier))
            logger.warning(
                "rate_limit_exceeded",
                extra={"identifier": identifier, "tier": tier, "limit": limit},
            )
            return False, int(current), limit

        return True, int(result), limit
