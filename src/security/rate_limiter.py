import time
import logging
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window rate limiter, keyed by client identifier (IP or API key).

    Uses an in-memory deque per key — suitable for single-process deployments.
    For multi-process, swap the per-key window for a Redis sorted-set backend.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        enabled: bool = True,
    ) -> None:
        self._limit = requests_per_minute
        self._enabled = enabled
        self._windows: dict[str, deque[float]] = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    def is_allowed(self, client_id: str) -> bool:
        if not self._enabled:
            return True

        now = time.monotonic()
        window_start = now - 60.0

        if client_id not in self._windows:
            self._windows[client_id] = deque()

        window = self._windows[client_id]

        # Evict timestamps outside the sliding window
        while window and window[0] < window_start:
            window.popleft()

        if len(window) >= self._limit:
            logger.warning(
                "rate_limit_exceeded", extra={"client_id": client_id[:40]}
            )
            return False

        window.append(now)
        return True

    def current_count(self, client_id: str) -> int:
        now = time.monotonic()
        window = self._windows.get(client_id, deque())
        return sum(1 for t in window if t > now - 60.0)
