import logging
import secrets

logger = logging.getLogger(__name__)

_SAFE_COMPARE_ITERATIONS = 100_000


class APIKeyManager:
    """Validates X-API-Key header against a configured set of keys.

    Keys are loaded from the API_KEYS environment variable as a
    comma-separated list. Empty = authentication disabled (dev mode).

    Keys are compared in constant time to prevent timing attacks.
    """

    def __init__(self, raw_keys: str = "") -> None:
        self._keys: set[str] = set()
        self._enabled = False

        if raw_keys.strip():
            for k in raw_keys.split(","):
                k = k.strip()
                if k:
                    self._keys.add(k)
            self._enabled = bool(self._keys)

        if self._enabled:
            logger.info(
                "api_key_auth_enabled", extra={"key_count": len(self._keys)}
            )
        else:
            logger.warning("api_key_auth_disabled_open_access")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def validate(self, provided_key: str | None) -> bool:
        if not self._enabled:
            return True
        if not provided_key:
            return False
        # Constant-time comparison against all configured keys
        return any(secrets.compare_digest(provided_key, k) for k in self._keys)

    @staticmethod
    def generate_key() -> str:
        return secrets.token_urlsafe(32)
