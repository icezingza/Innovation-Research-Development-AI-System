import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies import get_db_session
from src.auth.dependencies import CurrentTenant, get_jwt_secret
from src.auth.jwt_handler import create_access_token
from src.auth.models import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    TenantOut,
    TokenResponse,
    UserOut,
)
from src.auth.password import hash_password, verify_password
from src.auth.refresh_store import RefreshTokenStore
from src.tenants.context import SYSTEM_TENANT_ID
from src.tenants.models import TenantMember
from src.tenants.repository import TenantRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-")[:50]


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_session),
) -> RegisterResponse:
    async with session_factory() as session:
        repo = TenantRepository(session)
        if await repo.get_user_by_email(body.email):
            raise HTTPException(status_code=409, detail="Email already registered")
        slug = _slugify(body.org_name)
        if await repo.get_tenant_by_slug(slug):
            slug = f"{slug}-{body.email.split('@')[0]}"
        tenant = await repo.create_tenant(name=body.org_name, slug=slug)
        user = await repo.create_user(
            email=body.email,
            display_name=body.display_name,
            hashed_password=hash_password(body.password),
        )
        await repo.add_member(tenant_id=tenant.id, user_id=user.id, role="owner")
        await session.commit()

    secret = get_jwt_secret()
    access_token = create_access_token(
        user_id=user.id, tenant_id=tenant.id, role="owner", secret=secret
    )
    return RegisterResponse(
        access_token=access_token,
        user=UserOut(id=user.id, email=user.email, display_name=user.display_name),
        tenant=TenantOut(id=tenant.id, name=tenant.name, slug=tenant.slug),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_session),
) -> TokenResponse:
    async with session_factory() as session:
        repo = TenantRepository(session)
        user = await repo.get_user_by_email(body.email)
        if not user or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        result = await session.execute(
            select(TenantMember).where(TenantMember.user_id == user.id)
        )
        member = result.scalars().first()
        tenant_id = member.tenant_id if member else SYSTEM_TENANT_ID
        role = member.role if member else "member"

    secret = get_jwt_secret()
    access_token = create_access_token(
        user_id=user.id, tenant_id=tenant_id, role=role, secret=secret
    )
    refresh_store = RefreshTokenStore(request.app.state.redis)
    refresh_token = await refresh_store.create(user_id=user.id)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600,
    )
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_session),
) -> TokenResponse:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    refresh_store = RefreshTokenStore(request.app.state.redis)
    user_id = await refresh_store.get_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Refresh token invalid or expired")
    async with session_factory() as session:
        repo = TenantRepository(session)
        user = await repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        result = await session.execute(
            select(TenantMember).where(TenantMember.user_id == user.id)
        )
        member = result.scalars().first()
        tenant_id = member.tenant_id if member else SYSTEM_TENANT_ID
        role = member.role if member else "member"

    secret = get_jwt_secret()
    access_token = create_access_token(
        user_id=user.id, tenant_id=tenant_id, role=role, secret=secret
    )
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    request: Request, response: Response, tenant: CurrentTenant
) -> dict[str, str]:
    token = request.cookies.get("refresh_token")
    if token:
        refresh_store = RefreshTokenStore(request.app.state.redis)
        await refresh_store.revoke(token)
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=MeResponse)
async def me(
    request: Request,
    tenant: CurrentTenant,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_session),
) -> MeResponse:
    async with session_factory() as session:
        repo = TenantRepository(session)
        user = await repo.get_user_by_id(tenant.user_id)
        t = await repo.get_tenant_by_id(tenant.tenant_id)
        if not user or not t:
            raise HTTPException(status_code=404, detail="User or tenant not found")
    return MeResponse(
        user=UserOut(id=user.id, email=user.email, display_name=user.display_name),
        tenant=TenantOut(id=t.id, name=t.name, slug=t.slug),
        role=tenant.role,
    )
