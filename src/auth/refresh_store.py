import secrets
import logging
from datetime import timedelta
from typing import Optional

logger = logging.getLogger(__name__)

REFRESH_TOKEN_TTL = timedelta(days=7)
_KEY_PREFIX = "refresh:"


class RefreshTokenStore:
    def __init__(self, redis_client: object) -> None:
        # redis_client is an aioredis/redis.asyncio client
        self._redis = redis_client

    async def create(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        key = f"{_KEY_PREFIX}{token}"
        await self._redis.set(key, user_id, ex=int(REFRESH_TOKEN_TTL.total_seconds()))
        logger.info("Created refresh token for user_id=%s", user_id)
        return token

    async def get_user_id(self, token: str) -> Optional[str]:
        key = f"{_KEY_PREFIX}{token}"
        value = await self._redis.get(key)
        if value is None:
            return None
        # aioredis returns bytes or str depending on decode_responses setting
        return value.decode() if isinstance(value, bytes) else value

    async def revoke(self, token: str) -> None:
        key = f"{_KEY_PREFIX}{token}"
        await self._redis.delete(key)
        logger.info("Revoked refresh token")
