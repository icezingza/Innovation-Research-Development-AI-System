import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.tenants.context import TenantContext, SYSTEM_TENANT_ID

logger = logging.getLogger(__name__)

EXEMPT_PATHS = {"/health", "/metrics", "/auth/register", "/auth/login", "/auth/refresh"}


class TenantMiddleware(BaseHTTPMiddleware):
    """Injects TenantContext into request.state from X-Tenant-ID header.

    Reads X-Tenant-ID header and constructs TenantContext with:
    - tenant_id: from header or SYSTEM_TENANT_ID default
    - user_id: empty string (filled by JWT middleware in Phase 3B)
    - role: member (upgraded by JWT middleware in Phase 3B)

    Exempt paths (public endpoints and auth flows) default to SYSTEM_TENANT_ID.
    Dashboard paths also use SYSTEM_TENANT_ID.

    Note: JWT middleware (Phase 3B) will override tenant context with
    authenticated user data during request processing.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exempt paths: public health, metrics, auth endpoints
        if request.url.path in EXEMPT_PATHS or request.url.path.startswith(
            "/dashboard"
        ):
            request.state.tenant = TenantContext(
                tenant_id=SYSTEM_TENANT_ID,
                user_id="",
                role="member",
            )
            return await call_next(request)

        # Extract tenant ID from header, default to system tenant
        tenant_id = request.headers.get("X-Tenant-ID", SYSTEM_TENANT_ID)

        # Construct context (user_id and role will be filled by JWT middleware)
        request.state.tenant = TenantContext(
            tenant_id=tenant_id,
            user_id="",
            role="member",
        )
        return await call_next(request)
