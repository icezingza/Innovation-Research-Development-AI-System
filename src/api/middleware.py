import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_EXEMPT_PATHS = {"/health", "/metrics"}


class SecurityMiddleware(BaseHTTPMiddleware):
    """API key authentication + sliding-window rate limiting.

    Reads APIKeyManager and RateLimiter from app.state so they are
    created during lifespan and wired once. Exempt paths bypass all
    checks so health and metrics endpoints remain always accessible.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        key_manager = getattr(request.app.state, "key_manager", None)
        rate_limiter = getattr(request.app.state, "rate_limiter", None)

        # --- API key check ---
        if key_manager is not None and key_manager.enabled:
            provided_key = request.headers.get("X-API-Key")
            if not key_manager.validate(provided_key):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key"},
                )

        # --- Rate limiting ---
        if rate_limiter is not None and rate_limiter.enabled:
            provided_key = request.headers.get("X-API-Key")
            client_id = provided_key or (
                request.client.host if request.client else "unknown"
            )
            if not rate_limiter.is_allowed(client_id):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Retry after 60 seconds."},
                    headers={"Retry-After": "60"},
                )

        return await call_next(request)
