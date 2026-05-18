import logging
from typing import TYPE_CHECKING

from cryptography.fernet import Fernet

if TYPE_CHECKING:
    import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "cmk:"


class CMKManager:
    """Customer-Managed Encryption Keys — per-tenant Fernet key management.

    Keys are stored in Redis under 'cmk:{tenant_id}' with TTL=0 (permanent).
    Works in degraded mode (in-memory ephemeral keys) when Redis is unavailable.
    """

    def __init__(self, redis_client: "aioredis.Redis | None" = None) -> None:
        self._redis = redis_client
        self._local: dict[str, bytes] = {}

    def _redis_key(self, tenant_id: str) -> str:
        return f"{_KEY_PREFIX}{tenant_id}"

    async def _get_or_create_key(self, tenant_id: str) -> bytes:
        rkey = self._redis_key(tenant_id)
        if self._redis is not None:
            raw = await self._redis.get(rkey)
            if raw:
                return raw if isinstance(raw, bytes) else raw.encode()
            new_key = Fernet.generate_key()
            await self._redis.set(rkey, new_key)
            logger.info("cmk_key_created", extra={"tenant_id": tenant_id})
            return new_key

        # In-memory fallback
        if tenant_id not in self._local:
            self._local[tenant_id] = Fernet.generate_key()
            logger.info("cmk_key_created_local", extra={"tenant_id": tenant_id})
        return self._local[tenant_id]

    async def encrypt(self, tenant_id: str, plaintext: str) -> str:
        """Encrypt plaintext for a tenant. Returns URL-safe base64 token."""
        key = await self._get_or_create_key(tenant_id)
        token = Fernet(key).encrypt(plaintext.encode())
        return token.decode()

    async def decrypt(self, tenant_id: str, ciphertext: str) -> str:
        """Decrypt a token for a tenant. Raises InvalidToken on failure."""
        key = await self._get_or_create_key(tenant_id)
        plaintext = Fernet(key).decrypt(ciphertext.encode())
        return plaintext.decode()

    async def rotate_key(self, tenant_id: str) -> None:
        """Generate and store a fresh key for a tenant (old ciphertexts become invalid)."""
        new_key = Fernet.generate_key()
        if self._redis is not None:
            await self._redis.set(self._redis_key(tenant_id), new_key)
        else:
            self._local[tenant_id] = new_key
        logger.info("cmk_key_rotated", extra={"tenant_id": tenant_id})
