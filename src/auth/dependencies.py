import os
import logging
from typing import Annotated
from fastapi import Depends, HTTPException, status, Request
from src.tenants.context import TenantContext
from src.auth.jwt_handler import decode_access_token, InvalidTokenError

logger = logging.getLogger(__name__)


def get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")
    return secret


def get_current_tenant(request: Request) -> TenantContext:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header.removeprefix("Bearer ")
    secret = get_jwt_secret()
    try:
        payload = decode_access_token(token, secret)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TenantContext(
        tenant_id=payload["tenant_id"],
        user_id=payload["sub"],
        role=payload["role"],
    )


CurrentTenant = Annotated[TenantContext, Depends(get_current_tenant)]


def require_role(*roles: str):
    def dependency(tenant: CurrentTenant) -> TenantContext:
        if tenant.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {roles}",
            )
        return tenant

    return Depends(dependency)
