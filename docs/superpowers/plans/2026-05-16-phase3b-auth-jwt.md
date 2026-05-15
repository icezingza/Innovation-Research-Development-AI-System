# Phase 3B — Auth & API Gateway (JWT) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace X-API-Key auth with JWT-based authentication. Users register/login and receive tokens scoped to their tenant. All protected endpoints verify JWT and inject TenantContext.

**Architecture:** HS256 JWT (15 min access) + opaque refresh token in Redis (7 days). New `/auth/*` endpoints. JWTMiddleware replaces SecurityMiddleware for human callers; X-API-Key kept for service accounts.

**Tech Stack:** python-jose, bcrypt (passlib), FastAPI, Redis, Pydantic v2, pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/auth/__init__.py` | Create | Package init |
| `src/auth/password.py` | Create | bcrypt hash/verify |
| `src/auth/jwt_handler.py` | Create | JWT encode/decode, token creation |
| `src/auth/refresh_store.py` | Create | Redis refresh token storage |
| `src/auth/models.py` | Create | Pydantic request/response schemas |
| `src/auth/dependencies.py` | Create | FastAPI dependency: get_current_tenant |
| `src/api/routes/auth.py` | Create | /auth/* endpoints |
| `src/api/middleware.py` | Modify | Add JWT verification path |
| `src/api/main.py` | Modify | Register /auth router |
| `tests/test_auth.py` | Create | Auth unit + integration tests |
| `.env.example` | Modify | Add JWT_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES |
| `requirements.txt` | Modify | Add python-jose, passlib[bcrypt] |

---

## Task 1: Dependencies + Password Hashing

**Files:**
- Modify: `requirements.txt`
- Create: `src/auth/password.py`

- [ ] **Step 1: Add dependencies to requirements.txt**

```
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

Install:
```bash
pip install python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4
```

- [ ] **Step 2: Write failing test**

Create `tests/test_auth.py`:

```python
import pytest
from src.auth.password import hash_password, verify_password

def test_hash_password_returns_string():
    hashed = hash_password("secret123")
    assert isinstance(hashed, str)
    assert hashed != "secret123"

def test_verify_password_correct():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True

def test_verify_password_wrong():
    hashed = hash_password("mypassword")
    assert verify_password("wrong", hashed) is False

def test_hash_is_not_deterministic():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt uses random salt
```

- [ ] **Step 3: Run test — expect FAIL**

```bash
pytest tests/test_auth.py::test_hash_password_returns_string -v
```

Expected: `FAIL — cannot import 'hash_password'`

- [ ] **Step 4: Create src/auth/password.py**

```python
from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    return _ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _ctx.verify(plain, hashed)
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/test_auth.py -k "password" -v
```

Expected: `PASS — 4 tests passed`

- [ ] **Step 6: Commit**

```bash
git add src/auth/ tests/test_auth.py requirements.txt
git commit -m "feat(auth): bcrypt password hashing"
```

---

## Task 2: JWT Handler

**Files:**
- Create: `src/auth/jwt_handler.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_auth.py`:

```python
import os
os.environ.setdefault("JWT_SECRET", "test-secret-32-chars-minimum-ok!")

from src.auth.jwt_handler import create_access_token, decode_access_token, TokenPayload

def test_create_access_token_returns_string():
    token = create_access_token(user_id="u1", tenant_id="t1", role="member")
    assert isinstance(token, str)
    assert len(token) > 20

def test_decode_valid_token():
    token = create_access_token(user_id="u1", tenant_id="t1", role="admin")
    payload = decode_access_token(token)
    assert payload.sub == "u1"
    assert payload.tenant_id == "t1"
    assert payload.role == "admin"

def test_decode_invalid_token_raises():
    from src.auth.jwt_handler import InvalidTokenError
    with pytest.raises(InvalidTokenError):
        decode_access_token("not.a.token")

def test_expired_token_raises():
    from src.auth.jwt_handler import InvalidTokenError
    import time
    token = create_access_token(user_id="u1", tenant_id="t1", role="member", expires_seconds=-1)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_auth.py -k "token" -v
```

Expected: `FAIL — cannot import 'create_access_token'`

- [ ] **Step 3: Create src/auth/jwt_handler.py**

```python
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass

from jose import jwt, JWTError


class InvalidTokenError(Exception):
    pass


def _secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")
    return secret


_ALGORITHM = "HS256"
_DEFAULT_EXPIRE_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")) * 60


@dataclass(frozen=True)
class TokenPayload:
    sub: str        # user_id
    tenant_id: str
    role: str
    jti: str
    exp: int
    iat: int


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_seconds: int = _DEFAULT_EXPIRE_SECONDS,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_seconds)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> TokenPayload:
    try:
        data = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
        return TokenPayload(
            sub=data["sub"],
            tenant_id=data["tenant_id"],
            role=data["role"],
            jti=data["jti"],
            exp=data["exp"],
            iat=data["iat"],
        )
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_auth.py -k "token" -v
```

Expected: `PASS — 4 tests passed`

- [ ] **Step 5: Commit**

```bash
git add src/auth/jwt_handler.py
git commit -m "feat(auth): JWT HS256 encode/decode with expiry validation"
```

---

## Task 3: Refresh Token Store

**Files:**
- Create: `src/auth/refresh_store.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_auth.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.auth.refresh_store import RefreshTokenStore

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=b"user-123")
    redis.delete = AsyncMock(return_value=1)
    return redis

@pytest.mark.asyncio
async def test_store_refresh_token(mock_redis):
    store = RefreshTokenStore(mock_redis)
    token = await store.create("user-123")
    assert isinstance(token, str)
    mock_redis.set.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_id_from_token(mock_redis):
    store = RefreshTokenStore(mock_redis)
    user_id = await store.get_user_id("some-token")
    assert user_id == "user-123"

@pytest.mark.asyncio
async def test_revoke_token(mock_redis):
    store = RefreshTokenStore(mock_redis)
    result = await store.revoke("some-token")
    assert result is True
    mock_redis.delete.assert_called_once()
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_auth.py -k "refresh" -v
```

Expected: `FAIL — cannot import 'RefreshTokenStore'`

- [ ] **Step 3: Create src/auth/refresh_store.py**

```python
from __future__ import annotations

import secrets
from typing import Any

REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 3600  # 7 days
_PREFIX = "refresh:"


class RefreshTokenStore:
    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def create(self, user_id: str) -> str:
        token = secrets.token_urlsafe(48)
        await self._redis.set(
            f"{_PREFIX}{token}",
            user_id.encode(),
            ex=REFRESH_TOKEN_EXPIRE_SECONDS,
        )
        return token

    async def get_user_id(self, token: str) -> str | None:
        value = await self._redis.get(f"{_PREFIX}{token}")
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else value

    async def revoke(self, token: str) -> bool:
        deleted = await self._redis.delete(f"{_PREFIX}{token}")
        return bool(deleted)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_auth.py -k "refresh" -v
```

Expected: `PASS — 3 tests passed`

- [ ] **Step 5: Commit**

```bash
git add src/auth/refresh_store.py
git commit -m "feat(auth): Redis refresh token store with 7-day TTL"
```

---

## Task 4: Auth Pydantic Models + Dependencies

**Files:**
- Create: `src/auth/models.py`
- Create: `src/auth/dependencies.py`

- [ ] **Step 1: Create src/auth/models.py**

```python
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
    org_name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str | None

    class Config:
        from_attributes = True


class MeResponse(BaseModel):
    user: UserOut
    tenant_id: str
    role: str
```

- [ ] **Step 2: Create src/auth/dependencies.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.auth.jwt_handler import decode_access_token, InvalidTokenError
from src.tenancy.context import TenantContext

_bearer = HTTPBearer(auto_error=False)


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TenantContext:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return TenantContext(tenant_id=payload.tenant_id, user_id=payload.sub, role=payload.role)


def require_role(*roles: str):
    async def _check(ctx: TenantContext = Depends(get_current_tenant)) -> TenantContext:
        if ctx.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return ctx
    return _check
```

- [ ] **Step 3: Commit**

```bash
git add src/auth/models.py src/auth/dependencies.py
git commit -m "feat(auth): Pydantic auth models + get_current_tenant dependency"
```

---

## Task 5: Auth Routes

**Files:**
- Create: `src/api/routes/auth.py`

- [ ] **Step 1: Create src/api/routes/auth.py**

```python
from __future__ import annotations

import re
from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_tenant
from src.auth.jwt_handler import create_access_token, _DEFAULT_EXPIRE_SECONDS
from src.auth.models import LoginRequest, MeResponse, RegisterRequest, TokenResponse, UserOut
from src.auth.password import hash_password, verify_password
from src.auth.refresh_store import RefreshTokenStore
from src.tenancy.context import TenantContext
from src.tenancy.repository import TenantRepository

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _get_repo(request: Request) -> TenantRepository:
    session: AsyncSession = request.app.state.db_session
    return TenantRepository(session)


def _get_refresh_store(request: Request) -> RefreshTokenStore:
    return RefreshTokenStore(request.app.state.redis)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, response: Response) -> Any:
    repo = _get_repo(request)
    refresh_store = _get_refresh_store(request)

    if await repo.get_user_by_email(body.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    slug = _slugify(body.org_name)
    if await repo.get_tenant_by_slug(slug):
        slug = f"{slug}-{body.email.split('@')[0]}"

    async with request.app.state.db_session.begin():
        tenant = await repo.create_tenant(name=body.org_name, slug=slug)
        user = await repo.create_user(
            email=body.email,
            hashed_password=hash_password(body.password),
            display_name=body.display_name,
        )
        await repo.add_member(tenant_id=tenant.id, user_id=user.id, role="owner")

    access_token = create_access_token(user_id=user.id, tenant_id=tenant.id, role="owner")
    refresh_token = await refresh_store.create(user.id)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", max_age=7 * 86400)
    return TokenResponse(access_token=access_token, expires_in=_DEFAULT_EXPIRE_SECONDS)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, response: Response) -> Any:
    repo = _get_repo(request)
    refresh_store = _get_refresh_store(request)

    user = await repo.get_user_by_email(body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    role = await repo.get_member_role_for_user(user.id)
    tenant_id, role_str = role if role else ("system", "member")

    user.last_login_at = datetime.now(UTC)

    access_token = create_access_token(user_id=user.id, tenant_id=tenant_id, role=role_str)
    refresh_token = await refresh_store.create(user.id)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", max_age=7 * 86400)
    return TokenResponse(access_token=access_token, expires_in=_DEFAULT_EXPIRE_SECONDS)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response) -> Any:
    refresh_store = _get_refresh_store(request)
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    user_id = await refresh_store.get_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    repo = _get_repo(request)
    role = await repo.get_member_role_for_user(user_id)
    tenant_id, role_str = role if role else ("system", "member")

    await refresh_store.revoke(token)
    new_refresh = await refresh_store.create(user_id)
    response.set_cookie("refresh_token", new_refresh, httponly=True, samesite="lax", max_age=7 * 86400)

    access_token = create_access_token(user_id=user_id, tenant_id=tenant_id, role=role_str)
    return TokenResponse(access_token=access_token, expires_in=_DEFAULT_EXPIRE_SECONDS)


@router.post("/logout")
async def logout(request: Request, response: Response, ctx: TenantContext = Depends(get_current_tenant)) -> dict:
    refresh_store = _get_refresh_store(request)
    token = request.cookies.get("refresh_token")
    if token:
        await refresh_store.revoke(token)
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=MeResponse)
async def me(request: Request, ctx: TenantContext = Depends(get_current_tenant)) -> Any:
    repo = _get_repo(request)
    user = await repo.get_user_by_id(ctx.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return MeResponse(
        user=UserOut(id=user.id, email=user.email, display_name=user.display_name),
        tenant_id=ctx.tenant_id,
        role=ctx.role,
    )
```

- [ ] **Step 2: Register router in src/api/main.py**

```python
from src.api.routes.auth import router as auth_router

# In create_app(), after existing routers:
app.include_router(auth_router)
```

Also add `/auth` to exempt paths in `SecurityMiddleware`:

```python
# In src/api/middleware.py
_EXEMPT_PATHS = {"/health", "/metrics", "/auth/register", "/auth/login", "/auth/refresh", "/dashboard"}
```

- [ ] **Step 3: Add JWT_SECRET to .env.example**

```bash
# Auth
JWT_SECRET=change-me-to-a-random-32-char-secret
ACCESS_TOKEN_EXPIRE_MINUTES=15
```

- [ ] **Step 4: Run integration tests**

Add to `tests/test_auth.py`:

```python
from fastapi.testclient import TestClient
from src.api.main import create_app
from unittest.mock import patch, AsyncMock

def test_register_endpoint_exists():
    app = create_app()
    client = TestClient(app)
    # Without a real DB — just check route exists (not 404)
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "org_name": "Test Org"
    })
    assert response.status_code != 404

def test_login_bad_credentials_returns_401():
    # Stub DB to return no user
    app = create_app()
    client = TestClient(app)
    with patch("src.api.routes.auth._get_repo") as mock_repo:
        mock_repo.return_value.get_user_by_email = AsyncMock(return_value=None)
        response = client.post("/auth/login", json={"email": "x@x.com", "password": "bad"})
    assert response.status_code == 401
```

```bash
pytest tests/test_auth.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/auth/ src/api/routes/auth.py src/api/main.py src/api/middleware.py .env.example
git commit -m "feat(auth): JWT register/login/refresh/logout/me endpoints"
```

---

## Task 6: Run Full Test Suite

- [ ] **Step 1: Run all tests**

```bash
pytest --tb=short -q
```

Expected: 207+ tests pass, 0 failures.

- [ ] **Step 2: Run linter**

```bash
ruff check src/
```

Expected: 0 errors.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Phase 3B JWT Auth & API Gateway complete"
```
