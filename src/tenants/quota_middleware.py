"""Middleware that enforces per-tenant monthly API quotas (Hard Block, HTTP 429)."""

import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.security.auth_utils import decode_token
from src.tenants.context import SYSTEM_TENANT_ID
from src.tenants.quota import QuotaService

logger = logging.getLogger(__name__)

# Paths that never count toward quota (health probes, auth, metrics)
QUOTA_EXEMPT: set[str] = {"/health", "/metrics", "/auth/login", "/auth/register"}


class QuotaMiddleware(BaseHTTPMiddleware):
    """Count every non-exempt API call against the tenant's monthly quota.

    Runs after TenantMiddleware so request.state.tenant is already populated.
    Reads tenant tier from request.state.tenant_tier (set by TenantMiddleware
    or defaults to 'free' if missing).

    Returns HTTP 429 with JSON body when quota is exceeded.
    Adds X-Quota-Used and X-Quota-Limit headers to every response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip exempt paths
        if request.url.path in QUOTA_EXEMPT:
            return await call_next(request)

        quota: QuotaService | None = getattr(request.app.state, "quota_service", None)
        if quota is None:
            # Quota service unavailable — allow request (fail open)
            logger.warning("quota_service_unavailable — failing open")
            return await call_next(request)

        tenant_ctx = getattr(request.state, "tenant", None)
        tenant_id: str = getattr(tenant_ctx, "tenant_id", None) or SYSTEM_TENANT_ID

        # Fallback: extract tenant_id from JWT when X-Tenant-ID header is absent
        if tenant_id == SYSTEM_TENANT_ID:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                try:
                    payload = decode_token(auth[7:])
                    tenant_id = payload.get("tenant_id", tenant_id)
                except Exception:
                    pass

        tier: str = getattr(request.state, "tenant_tier", "free")

        allowed, usage, limit = await quota.check_and_increment(tenant_id, tier)

        if not allowed:
            return Response(
                content=json.dumps(
                    {
                        "detail": "Monthly API quota exceeded",
                        "tier": tier,
                        "limit": limit,
                        "used": usage,
                    }
                ),
                status_code=429,
                media_type="application/json",
                headers={
                    "X-Quota-Used": str(usage),
                    "X-Quota-Limit": str(limit),
                    "Retry-After": "see X-Quota-Reset",
                },
            )

        response = await call_next(request)
        response.headers["X-Quota-Used"] = str(usage)
        response.headers["X-Quota-Limit"] = str(limit)
        return response
