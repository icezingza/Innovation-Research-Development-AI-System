import logging

from sqlalchemy.future import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.tenants.context import TenantContext, SYSTEM_TENANT_ID

logger = logging.getLogger(__name__)

EXEMPT_PATHS = {"/health", "/metrics", "/auth/register", "/auth/login", "/auth/refresh"}


class TenantMiddleware(BaseHTTPMiddleware):
    """Injects TenantContext + tenant_tier into request.state.

    Resolution order for tenant_id:
      1. X-Tenant-ID request header
      2. SYSTEM_TENANT_ID (fallback / exempt paths)

    Resolution order for tier:
      1. DB lookup on the resolved tenant_id (async, via app.state.db_session)
      2. 'free' (fallback when DB is unavailable or tenant not found)

    Sets:
      request.state.tenant      → TenantContext(tenant_id, user_id, role)
      request.state.tenant_tier → str  ("free" | "pro" | "enterprise")
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exempt paths always run as system tenant, free tier
        if request.url.path in EXEMPT_PATHS or request.url.path.startswith(
            "/dashboard"
        ):
            request.state.tenant = TenantContext(
                tenant_id=SYSTEM_TENANT_ID,
                user_id="",
                role="member",
            )
            request.state.tenant_tier = "free"
            return await call_next(request)

        # Resolve tenant_id from header
        tenant_id = request.headers.get("X-Tenant-ID", SYSTEM_TENANT_ID)

        request.state.tenant = TenantContext(
            tenant_id=tenant_id,
            user_id="",
            role="member",
        )

        # Resolve tier from DB (best-effort; fall back to 'free')
        request.state.tenant_tier = await self._resolve_tier(request, tenant_id)

        return await call_next(request)

    async def _resolve_tier(self, request: Request, tenant_id: str) -> str:
        """Look up the tenant's tier from the DB; return 'free' on any failure."""
        if tenant_id == SYSTEM_TENANT_ID:
            return "free"

        session_factory = getattr(request.app.state, "db_session", None)
        if session_factory is None:
            return "free"

        try:
            # Import here to avoid circular imports at module load time
            from src.memory.schema import Tenant

            async with session_factory() as session:
                result = await session.execute(
                    select(Tenant.tier).where(Tenant.id == tenant_id)
                )
                row = result.scalar_one_or_none()
                return row if row else "free"
        except Exception as exc:
            logger.warning(
                "tenant_tier_lookup_failed",
                extra={"tenant_id": tenant_id, "error": str(exc)},
            )
            return "free"
