"""Multi-tenant hardware isolation middleware.

Enforces per-tenant resource limits at the application layer:
  - max concurrent requests per tenant (prevents noisy-neighbor CPU starvation)
  - request admission control based on tier ResourcePolicy

Physical isolation (K8s ResourceQuota / cgroups) is defined in:
  k8s/resource-quotas/  — one ResourceQuota manifest per tier

This middleware is the application-layer enforcement complement to
infrastructure-layer physical resource limits.
"""

import asyncio
import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.tenants.context import SYSTEM_TENANT_ID
from src.tenants.resource_policy import ResourcePolicy, get_policy

logger = logging.getLogger(__name__)

# Paths that bypass resource isolation (health probes, metrics)
ISOLATION_EXEMPT: set[str] = {"/health", "/metrics"}


class TenantConcurrencyTracker:
    """Thread-safe in-process concurrency counter per tenant.

    In a multi-process deployment (e.g., gunicorn workers), replace
    the local dict with a Redis INCR/DECR on the same key pattern.
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, tenant_id: str, max_concurrent: int) -> bool:
        """Atomically increment if below limit. Returns True if acquired."""
        async with self._lock:
            current = self._counts.get(tenant_id, 0)
            if current >= max_concurrent:
                return False
            self._counts[tenant_id] = current + 1
            return True

    async def release(self, tenant_id: str) -> None:
        async with self._lock:
            current = self._counts.get(tenant_id, 0)
            self._counts[tenant_id] = max(0, current - 1)

    async def current(self, tenant_id: str) -> int:
        async with self._lock:
            return self._counts.get(tenant_id, 0)

    async def snapshot(self) -> dict[str, int]:
        async with self._lock:
            return dict(self._counts)


# Module-level singleton — shared across all requests in the process
_tracker = TenantConcurrencyTracker()


def get_tracker() -> TenantConcurrencyTracker:
    return _tracker


class ResourceIsolationMiddleware(BaseHTTPMiddleware):
    """Admit or reject requests based on per-tenant tier resource policy.

    Sets X-Resource-Policy and X-Concurrent-Requests response headers
    so operators can observe isolation enforcement in API logs.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ISOLATION_EXEMPT:
            return await call_next(request)

        tenant_ctx = getattr(request.state, "tenant", None)
        tenant_id: str = (
            getattr(tenant_ctx, "tenant_id", None) or SYSTEM_TENANT_ID
        )
        tier: str = getattr(request.state, "tenant_tier", "free")
        policy: ResourcePolicy = get_policy(tier)

        # Attach policy info to request state for downstream use
        request.state.resource_policy = policy

        acquired = await _tracker.acquire(tenant_id, policy.max_concurrent_requests)
        if not acquired:
            current = await _tracker.current(tenant_id)
            logger.warning(
                "resource_isolation_rejected",
                extra={
                    "tenant_id": tenant_id,
                    "tier": tier,
                    "concurrent": current,
                    "limit": policy.max_concurrent_requests,
                },
            )
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Concurrent request limit reached for your tier",
                    "tier": tier,
                    "max_concurrent_requests": policy.max_concurrent_requests,
                    "current_concurrent_requests": current,
                    "upgrade_message": "Upgrade to enterprise tier for dedicated resource headroom",
                },
                headers={
                    "X-Resource-Policy": tier,
                    "Retry-After": "1",
                },
            )

        try:
            response = await call_next(request)
        finally:
            await _tracker.release(tenant_id)

        response.headers["X-Resource-Policy"] = tier
        response.headers["X-Max-Concurrent"] = str(policy.max_concurrent_requests)
        return response


async def get_resource_snapshot() -> dict[str, Any]:
    """Return current concurrency state for all active tenants."""
    return await _tracker.snapshot()
