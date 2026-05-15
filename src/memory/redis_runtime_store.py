import json
from typing import Any

import redis.asyncio as redis


class RedisRuntimeStore:
    """Runtime state synchronization via Redis."""

    def __init__(self, url: str = "redis://localhost:6379") -> None:
        self.client: redis.Redis = redis.from_url(url, decode_responses=True)

    async def healthcheck(self) -> bool:
        await self.client.ping()
        return True

    async def set_state(
        self, key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        if ttl_seconds is not None:
            await self.client.setex(key, ttl_seconds, serialized)
        else:
            await self.client.set(key, serialized)

    async def get_state(self, key: str) -> Any:
        raw = await self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def delete_state(self, key: str) -> None:
        await self.client.delete(key)

    async def close(self) -> None:
        await self.client.aclose()
