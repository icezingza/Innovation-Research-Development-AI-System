# Phase 3A — Multi-tenant Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add tenant/user/role tables, migrate all existing tables with `tenant_id`, and scope all DB queries by tenant.

**Architecture:** Row-level isolation via `tenant_id` FK on all tables. System tenant seeds backward compat. TenantContext injected via `request.state.tenant` (dev: X-Tenant-ID header; prod: JWT in Phase 3B).

**Tech Stack:** SQLAlchemy, Alembic, PostgreSQL, FastAPI, Pydantic v2, bcrypt, pytest-asyncio

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/memory/schema.py` | Modify | Add Tenant, User, TenantMember models + tenant_id to existing |
| `alembic/versions/002_tenant_schema.py` | Create | New tenant/user/member tables + system tenant seed |
| `alembic/versions/003_add_tenant_id.py` | Create | Add tenant_id to 4 existing tables |
| `src/tenancy/__init__.py` | Create | Package init |
| `src/tenancy/context.py` | Create | TenantContext dataclass |
| `src/tenancy/middleware.py` | Create | TenantMiddleware (reads X-Tenant-ID dev header or JWT later) |
| `src/tenancy/repository.py` | Create | Tenant/User DB operations |
| `src/memory/research_memory.py` | Modify | Add tenant_id param to recall/store |
| `src/api/main.py` | Modify | Register TenantMiddleware |
| `tests/test_tenancy.py` | Create | Tenant context + middleware tests |
| `tests/test_migrations.py` | Create | Schema migration tests |

---

## Task 1: Tenant Schema Models

**Files:**
- Modify: `src/memory/schema.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_tenancy.py`:

```python
import pytest
from sqlalchemy import create_engine, inspect
from src.memory.schema import Base, Tenant, User, TenantMember, WorkflowRecord

@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng

def test_tenant_table_exists(engine):
    inspector = inspect(engine)
    assert "tenants" in inspector.get_table_names()

def test_users_table_exists(engine):
    inspector = inspect(engine)
    assert "users" in inspector.get_table_names()

def test_tenant_members_table_exists(engine):
    inspector = inspect(engine)
    assert "tenant_members" in inspector.get_table_names()

def test_workflow_has_tenant_id(engine):
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("workflow_records")]
    assert "tenant_id" in cols

def test_hypothesis_has_tenant_id(engine):
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("hypothesis_records")]
    assert "tenant_id" in cols
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_tenancy.py -v
```

Expected: `FAIL — cannot import name 'Tenant' from src.memory.schema`

- [ ] **Step 3: Add models to src/memory/schema.py**

Add after existing imports:

```python
import uuid
from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# ── Tenant ────────────────────────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

# ── TenantMember ──────────────────────────────────────────────────────────────

class TenantMember(Base):
    __tablename__ = "tenant_members"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

Also add `tenant_id` to existing models:

```python
# In WorkflowRecord — add column:
tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

# In HypothesisRecord — add column:
tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

# In ReasoningTraceRecord — add column:
tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

# In ResearchTask — add column:
tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/test_tenancy.py -v
```

Expected: `PASS — 5 tests passed`

- [ ] **Step 5: Commit**

```bash
git add src/memory/schema.py tests/test_tenancy.py
git commit -m "feat(tenancy): add Tenant, User, TenantMember models + tenant_id to existing tables"
```

---

## Task 2: Alembic Migration 002 — Tenant Tables

**Files:**
- Create: `alembic/versions/002_tenant_schema.py`

- [ ] **Step 1: Create migration**

```python
# alembic/versions/002_tenant_schema.py
"""Create tenant, user, tenant_member tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000001"

def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "tenant_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )

    # Seed system tenant for backward compat
    op.execute(
        f"INSERT INTO tenants (id, name, slug, plan) "
        f"VALUES ('{SYSTEM_TENANT_ID}', 'System', 'system', 'enterprise')"
    )

def downgrade() -> None:
    op.drop_table("tenant_members")
    op.drop_table("users")
    op.drop_table("tenants")
```

- [ ] **Step 2: Run migration on dev database**

```bash
alembic upgrade 002
```

Expected: `Running upgrade 001 -> 002` with no errors.

- [ ] **Step 3: Verify tables created**

```bash
alembic current
```

Expected: `002 (head)`

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/002_tenant_schema.py
git commit -m "feat(tenancy): migration 002 — create tenant/user/member tables + system tenant seed"
```

---

## Task 3: Alembic Migration 003 — Add tenant_id

**Files:**
- Create: `alembic/versions/003_add_tenant_id.py`

- [ ] **Step 1: Create migration**

```python
# alembic/versions/003_add_tenant_id.py
"""Add tenant_id to all existing resource tables

Revision ID: 003
Revises: 002
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000001"
TABLES = ["workflow_records", "hypothesis_records", "reasoning_traces", "research_tasks"]

def upgrade() -> None:
    for table in TABLES:
        # Step 1: add nullable
        op.add_column(table, sa.Column("tenant_id", sa.String(36), nullable=True))

    # Step 2: backfill existing rows with system tenant
    for table in TABLES:
        op.execute(f"UPDATE {table} SET tenant_id = '{SYSTEM_TENANT_ID}' WHERE tenant_id IS NULL")

    # Step 3: add FK + NOT NULL + index
    for table in TABLES:
        op.alter_column(table, "tenant_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_tenant_id", table, "tenants", ["tenant_id"], ["id"]
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

def downgrade() -> None:
    for table in TABLES:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")
```

- [ ] **Step 2: Run migration**

```bash
alembic upgrade 003
```

Expected: `Running upgrade 002 -> 003`

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/003_add_tenant_id.py
git commit -m "feat(tenancy): migration 003 — add tenant_id to all resource tables + backfill system tenant"
```

---

## Task 4: TenantContext + Middleware

**Files:**
- Create: `src/tenancy/__init__.py`
- Create: `src/tenancy/context.py`
- Create: `src/tenancy/middleware.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_tenancy.py`:

```python
from src.tenancy.context import TenantContext
from src.tenancy.middleware import TenantMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient

SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000001"

def test_tenant_context_fields():
    ctx = TenantContext(tenant_id="t1", user_id="u1", role="member")
    assert ctx.tenant_id == "t1"
    assert ctx.user_id == "u1"
    assert ctx.role == "member"

def test_tenant_middleware_injects_context():
    app = FastAPI()

    @app.get("/test")
    async def handler(request):
        from fastapi import Request
        ctx = request.state.tenant
        return {"tenant_id": ctx.tenant_id}

    app.add_middleware(TenantMiddleware)
    client = TestClient(app)
    response = client.get("/test", headers={"X-Tenant-ID": "abc-123", "X-User-ID": "usr-456"})
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "abc-123"

def test_tenant_middleware_uses_system_tenant_when_no_header():
    app = FastAPI()

    @app.get("/test")
    async def handler(request):
        from fastapi import Request
        ctx = request.state.tenant
        return {"tenant_id": ctx.tenant_id}

    app.add_middleware(TenantMiddleware)
    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json()["tenant_id"] == SYSTEM_TENANT_ID
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_tenancy.py::test_tenant_context_fields -v
```

Expected: `FAIL — cannot import name 'TenantContext'`

- [ ] **Step 3: Create src/tenancy/__init__.py**

```python
from src.tenancy.context import TenantContext

__all__ = ["TenantContext"]
```

- [ ] **Step 4: Create src/tenancy/context.py**

```python
from dataclasses import dataclass

SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000001"
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000002"


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    user_id: str
    role: str  # owner | admin | member

    @classmethod
    def system(cls) -> "TenantContext":
        return cls(tenant_id=SYSTEM_TENANT_ID, user_id=SYSTEM_USER_ID, role="owner")
```

- [ ] **Step 5: Create src/tenancy/middleware.py**

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.tenancy.context import TenantContext, SYSTEM_TENANT_ID, SYSTEM_USER_ID


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: ...) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID", SYSTEM_TENANT_ID)
        user_id = request.headers.get("X-User-ID", SYSTEM_USER_ID)
        role = request.headers.get("X-Tenant-Role", "member")

        request.state.tenant = TenantContext(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )
        return await call_next(request)
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
pytest tests/test_tenancy.py -v
```

Expected: `PASS — 8 tests passed`

- [ ] **Step 7: Register TenantMiddleware in src/api/main.py**

Add after existing middleware registration:

```python
from src.tenancy.middleware import TenantMiddleware

# In create_app():
app.add_middleware(TenantMiddleware)  # add before SecurityMiddleware
```

- [ ] **Step 8: Commit**

```bash
git add src/tenancy/ src/api/main.py
git commit -m "feat(tenancy): TenantContext + TenantMiddleware with dev X-Tenant-ID header"
```

---

## Task 5: Tenant Repository

**Files:**
- Create: `src/tenancy/repository.py`

- [ ] **Step 1: Create repository**

```python
# src/tenancy/repository.py
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.memory.schema import Tenant, User, TenantMember


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        result = await self._session.execute(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        result = await self._session.execute(
            select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)
        )
        return result.scalar_one_or_none()

    async def create_tenant(self, name: str, slug: str, plan: str = "free") -> Tenant:
        tenant = Tenant(id=str(uuid.uuid4()), name=name, slug=slug, plan=plan)
        self._session.add(tenant)
        await self._session.flush()
        return tenant

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        return result.scalar_one_or_none()

    async def create_user(self, email: str, hashed_password: str, display_name: str | None = None) -> User:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hashed_password,
            display_name=display_name,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def add_member(self, tenant_id: str, user_id: str, role: str = "member") -> TenantMember:
        member = TenantMember(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )
        self._session.add(member)
        await self._session.flush()
        return member

    async def get_member_role(self, tenant_id: str, user_id: str) -> Optional[str]:
        result = await self._session.execute(
            select(TenantMember.role).where(
                TenantMember.tenant_id == tenant_id,
                TenantMember.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        return row
```

- [ ] **Step 2: Commit**

```bash
git add src/tenancy/repository.py
git commit -m "feat(tenancy): TenantRepository for tenant/user/member CRUD"
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
git commit -m "feat: Phase 3A Multi-tenant infrastructure complete"
```
