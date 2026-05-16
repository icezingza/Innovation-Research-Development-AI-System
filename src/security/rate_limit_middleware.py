"""Per-tenant sliding-window rate limit middleware (HTTP 429 on burst abuse)."""
import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.security.auth_utils import decode_token
from src.security.redis_rate_limiter import RedisRateLimiter
from src.tenants.context import SYSTEM_TENANT_ID

logger = logging.getLogger(__name__)

RATE_LIMIT_EXEMPT: set[str] = {"/health", "/metrics", "/auth/login", "/auth/register"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce per-tenant per-minute request limits using Redis sliding window.

    Identifier priority:
      1. tenant_id from request.state.tenant (set by TenantMiddleware via header)
      2. tenant_id decoded from JWT Authorization header (fallback)
      3. Client IP address (last resort — e.g. unauthenticated requests)

    Adds X-RateLimit-Limit and X-RateLimit-Remaining headers to every response.
    Returns HTTP 429 with Retry-After: 60 on burst abuse.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in RATE_LIMIT_EXEMPT:
            return await call_next(request)

        limiter: RedisRateLimiter | None = getattr(
            request.app.state, "redis_rate_limiter", None
        )
        if limiter is None:
            return await call_next(request)

        identifier, tier = self._resolve_identity(request)
        allowed, count, limit = await limiter.is_allowed(identifier, tier)

        if not allowed:
            return Response(
                content=json.dumps({
                    "detail": "Rate limit exceeded — too many requests per minute",
                    "limit": limit,
                    "retry_after_seconds": 60,
                }),
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        remaining = max(0, limit - count)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    def _resolve_identity(self, request: Request) -> tuple[str, str]:
        """Return (identifier, tier) for rate-limit key selection."""
        # 1. TenantMiddleware populated request.state.tenant
        tenant_ctx = getattr(request.state, "tenant", None)
        tenant_id: str | None = getattr(tenant_ctx, "tenant_id", None)
        tier: str = getattr(request.state, "tenant_tier", "free")

        # 2. Fallback: decode JWT when no header-based tenant
        if not tenant_id or tenant_id == SYSTEM_TENANT_ID:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                try:
                    payload = decode_token(auth[7:])
                    tenant_id = payload.get("tenant_id") or tenant_id
                except Exception:
                    pass

        # 3. Last resort: client IP
        if not tenant_id or tenant_id == SYSTEM_TENANT_ID:
            tenant_id = (request.client.host if request.client else "unknown")

        return tenant_id, tier
