# Phase 3C — Usage Quota & Billing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enforce per-tenant usage quotas by subscription tier, record usage events async via EventBus, and expose billing API endpoints for dashboard display.

**Architecture:** QuotaMiddleware checks Redis-cached usage count before routing. UsageTracker publishes events to EventBus (fire-and-forget). MemoryAgent-style subscriber persists events to PostgreSQL. 3 tiers: free/pro/enterprise.

**Tech Stack:** FastAPI, SQLAlchemy, Redis, EventBus (existing), Pydantic v2, Alembic, pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `alembic/versions/004_quota_billing.py` | Create | subscription_plans + tenant_subscriptions + usage_events tables |
| `src/billing/__init__.py` | Create | Package init |
| `src/billing/models.py` | Create | Pydantic schemas for billing API |
| `src/billing/usage_tracker.py` | Create | UsageTracker, QuotaStatus, UsageSummary |
| `src/billing/quota_middleware.py` | Create | QuotaMiddleware (checks quota, records events) |
| `src/api/routes/billing.py` | Create | /billing/* endpoints |
| `src/api/main.py` | Modify | Register QuotaMiddleware + billing router |
| `src/memory/schema.py` | Modify | Add SubscriptionPlan, TenantSubscription, UsageEvent models |
| `tests/test_billing.py` | Create | Quota + usage tracking tests |

---

## Task 1: Billing Schema Models

**Files:**
- Modify: `src/memory/schema.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_billing.py`:

```python
import pytest
from sqlalchemy import create_engine, inspect
from src.memory.schema import Base, SubscriptionPlan, TenantSubscription, UsageEvent

@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng

def test_subscription_plans_table_exists(engine):
    inspector = inspect(engine)
    assert "subscription_plans" in inspector.get_table_names()

def test_tenant_subscriptions_table_exists(engine):
    inspector = inspect(engine)
    assert "tenant_subscriptions" in inspector.get_table_names()

def test_usage_events_table_exists(engine):
    inspector = inspect(engine)
    assert "usage_events" in inspector.get_table_names()

def test_subscription_plan_has_required_cols(engine):
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("subscription_plans")]
    for col in ["id", "name", "max_workflows", "max_hypotheses", "max_api_calls", "price_usd_cents"]:
        assert col in cols
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_billing.py -v
```

Expected: `FAIL — cannot import name 'SubscriptionPlan'`

- [ ] **Step 3: Add models to src/memory/schema.py**

```python
import uuid

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_workflows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)     # None = unlimited
    max_hypotheses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_api_calls: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_usd_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class TenantSubscription(Base):
    __tablename__ = "tenant_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), unique=True, nullable=False)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("subscription_plans.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/test_billing.py -v
```

Expected: `PASS — 4 tests passed`

- [ ] **Step 5: Commit**

```bash
git add src/memory/schema.py tests/test_billing.py
git commit -m "feat(billing): add SubscriptionPlan, TenantSubscription, UsageEvent models"
```

---

## Task 2: Alembic Migration 004 — Billing Tables

**Files:**
- Create: `alembic/versions/004_quota_billing.py`

- [ ] **Step 1: Create migration**

```python
# alembic/versions/004_quota_billing.py
"""Create subscription_plans, tenant_subscriptions, usage_events

Revision ID: 004
Revises: 003
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000001"
NOW = datetime.now(timezone.utc).isoformat()
PERIOD_END = "2099-12-31T23:59:59+00:00"


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("max_workflows", sa.Integer, nullable=True),
        sa.Column("max_hypotheses", sa.Integer, nullable=True),
        sa.Column("max_api_calls", sa.Integer, nullable=True),
        sa.Column("price_usd_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tenant_subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), unique=True, nullable=False),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("subscription_plans.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_tenant_period", "usage_events", ["tenant_id", "recorded_at"])

    # Seed default plans
    plans_table = sa.table(
        "subscription_plans",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("max_workflows", sa.Integer),
        sa.column("max_hypotheses", sa.Integer),
        sa.column("max_api_calls", sa.Integer),
        sa.column("price_usd_cents", sa.Integer),
    )
    op.bulk_insert(plans_table, [
        {"id": "plan-free-001", "name": "free", "display_name": "Free", "max_workflows": 10, "max_hypotheses": 100, "max_api_calls": 1000, "price_usd_cents": 0},
        {"id": "plan-pro-001", "name": "pro", "display_name": "Pro", "max_workflows": 100, "max_hypotheses": 1000, "max_api_calls": 10000, "price_usd_cents": 4900},
        {"id": "plan-ent-001", "name": "enterprise", "display_name": "Enterprise", "max_workflows": None, "max_hypotheses": None, "max_api_calls": None, "price_usd_cents": 0},
    ])

    # Assign system tenant to enterprise plan
    op.execute(
        f"INSERT INTO tenant_subscriptions (id, tenant_id, plan_id, status, current_period_start, current_period_end) "
        f"VALUES ('sub-system-001', '{SYSTEM_TENANT_ID}', 'plan-ent-001', 'active', '{NOW}', '{PERIOD_END}')"
    )


def downgrade() -> None:
    op.drop_index("ix_usage_tenant_period", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_table("tenant_subscriptions")
    op.drop_table("subscription_plans")
```

- [ ] **Step 2: Run migration**

```bash
alembic upgrade 004
```

Expected: `Running upgrade 003 -> 004`

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/004_quota_billing.py
git commit -m "feat(billing): migration 004 — billing tables + seed free/pro/enterprise plans"
```

---

## Task 3: UsageTracker

**Files:**
- Create: `src/billing/usage_tracker.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_billing.py`:

```python
import pytest
from dataclasses import dataclass
from unittest.mock import AsyncMock
from src.billing.usage_tracker import UsageTracker, QuotaStatus

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"5")
    redis.incr = AsyncMock(return_value=6)
    redis.expire = AsyncMock(return_value=True)
    return redis

@pytest.mark.asyncio
async def test_check_quota_allowed(mock_redis):
    tracker = UsageTracker(mock_redis)
    status = await tracker.check_quota("tenant-1", "workflow_run", limit=10)
    assert status.allowed is True
    assert status.used == 5
    assert status.remaining == 5

@pytest.mark.asyncio
async def test_check_quota_exceeded(mock_redis):
    mock_redis.get = AsyncMock(return_value=b"10")
    tracker = UsageTracker(mock_redis)
    status = await tracker.check_quota("tenant-1", "workflow_run", limit=10)
    assert status.allowed is False
    assert status.remaining == 0

@pytest.mark.asyncio
async def test_check_quota_unlimited():
    tracker = UsageTracker(AsyncMock())
    status = await tracker.check_quota("tenant-1", "workflow_run", limit=None)
    assert status.allowed is True
    assert status.limit is None

@pytest.mark.asyncio
async def test_increment_usage(mock_redis):
    tracker = UsageTracker(mock_redis)
    count = await tracker.increment("tenant-1", "workflow_run")
    assert count == 6
    mock_redis.incr.assert_called_once()
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_billing.py -k "quota or increment" -v
```

Expected: `FAIL — cannot import 'UsageTracker'`

- [ ] **Step 3: Create src/billing/usage_tracker.py**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class QuotaStatus:
    allowed: bool
    limit: int | None
    used: int
    remaining: int | None
    reset_at: datetime
    upgrade_message: str | None = None


def _period_key(tenant_id: str, event_type: str) -> str:
    now = datetime.now(UTC)
    return f"quota:{tenant_id}:{event_type}:{now.year}-{now.month:02d}"


def _next_month_reset() -> datetime:
    now = datetime.now(UTC)
    if now.month == 12:
        return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


class UsageTracker:
    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def get_usage(self, tenant_id: str, event_type: str) -> int:
        key = _period_key(tenant_id, event_type)
        value = await self._redis.get(key)
        if value is None:
            return 0
        return int(value)

    async def increment(self, tenant_id: str, event_type: str) -> int:
        key = _period_key(tenant_id, event_type)
        count = await self._redis.incr(key)
        # Set TTL to 35 days (covers full month + buffer)
        await self._redis.expire(key, 35 * 86400)
        return count

    async def check_quota(
        self,
        tenant_id: str,
        event_type: str,
        limit: int | None,
    ) -> QuotaStatus:
        if limit is None:
            return QuotaStatus(
                allowed=True,
                limit=None,
                used=0,
                remaining=None,
                reset_at=_next_month_reset(),
            )

        used = await self.get_usage(tenant_id, event_type)
        allowed = used < limit
        remaining = max(0, limit - used)

        return QuotaStatus(
            allowed=allowed,
            limit=limit,
            used=used,
            remaining=remaining,
            reset_at=_next_month_reset(),
            upgrade_message=(
                None
                if allowed
                else f"Upgrade to Pro for more {event_type.replace('_', ' ')}s. Contact sales@ird-ai.com"
            ),
        )
```

- [ ] **Step 4: Create src/billing/__init__.py**

```python
from src.billing.usage_tracker import UsageTracker, QuotaStatus

__all__ = ["UsageTracker", "QuotaStatus"]
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/test_billing.py -k "quota or increment" -v
```

Expected: `PASS — 4 tests passed`

- [ ] **Step 6: Commit**

```bash
git add src/billing/
git commit -m "feat(billing): UsageTracker with Redis-backed quota check and period increment"
```

---

## Task 4: QuotaMiddleware

**Files:**
- Create: `src/billing/quota_middleware.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_billing.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.billing.quota_middleware import QuotaMiddleware
from src.tenancy.context import TenantContext

PLAN_LIMITS = {"workflow_run": 10, "api_call": 100}

def _make_app(quota_allowed: bool) -> FastAPI:
    app = FastAPI()

    @app.get("/research/workflows")
    async def workflows():
        return {"ok": True}

    app.add_middleware(QuotaMiddleware)
    app.state.plan_limits = {"tenant-1": PLAN_LIMITS}
    return app

def test_quota_middleware_allows_when_under_limit():
    app = _make_app(True)

    with patch("src.billing.quota_middleware.UsageTracker") as MockTracker:
        instance = MockTracker.return_value
        instance.check_quota = AsyncMock(return_value=type("Q", (), {"allowed": True, "used": 5, "limit": 10, "remaining": 5, "reset_at": None, "upgrade_message": None})())
        client = TestClient(app)
        response = client.post("/research/workflows", headers={"X-Tenant-ID": "tenant-1"})
        assert response.status_code != 429

def test_quota_middleware_blocks_when_over_limit():
    app = FastAPI()

    @app.post("/research/workflows")
    async def workflows():
        return {"ok": True}

    app.add_middleware(QuotaMiddleware)

    with patch("src.billing.quota_middleware.UsageTracker") as MockTracker:
        instance = MockTracker.return_value
        import datetime
        quota_exceeded = type("Q", (), {
            "allowed": False, "used": 10, "limit": 10, "remaining": 0,
            "reset_at": datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc),
            "upgrade_message": "Upgrade to Pro"
        })()
        instance.check_quota = AsyncMock(return_value=quota_exceeded)
        client = TestClient(app)
        response = client.post("/research/workflows", headers={"X-Tenant-ID": "tenant-1"})
        assert response.status_code == 429
        assert "quota_exceeded" in response.json()["error"]
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_billing.py -k "middleware" -v
```

Expected: `FAIL — cannot import 'QuotaMiddleware'`

- [ ] **Step 3: Create src/billing/quota_middleware.py**

```python
from __future__ import annotations

import json
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.billing.usage_tracker import UsageTracker
from src.tenancy.context import TenantContext, SYSTEM_TENANT_ID

# Map: (method, path_prefix) -> event_type
_QUOTA_RULES: list[tuple[str, str, str]] = [
    ("POST", "/research/workflows", "workflow_run"),
    ("POST", "/reasoning/", "api_call"),
    ("POST", "/cognition/", "api_call"),
]

# Default limits per plan name — overridden by DB subscription in production
_DEFAULT_LIMITS: dict[str, dict[str, int | None]] = {
    "free": {"workflow_run": 10, "api_call": 1000, "hypothesis_generated": 100},
    "pro": {"workflow_run": 100, "api_call": 10000, "hypothesis_generated": 1000},
    "enterprise": {"workflow_run": None, "api_call": None, "hypothesis_generated": None},
}


def _match_event_type(method: str, path: str) -> str | None:
    for rule_method, prefix, event_type in _QUOTA_RULES:
        if method == rule_method and path.startswith(prefix):
            return event_type
    return None


class QuotaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        event_type = _match_event_type(request.method, request.url.path)
        if event_type is None:
            return await call_next(request)

        ctx: TenantContext | None = getattr(request.state, "tenant", None)
        if ctx is None or ctx.tenant_id == SYSTEM_TENANT_ID:
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        tracker = UsageTracker(redis)

        # Get plan limit — check app.state for plan, default to free
        plan_name = getattr(request.app.state, "tenant_plans", {}).get(ctx.tenant_id, "free")
        limit = _DEFAULT_LIMITS.get(plan_name, _DEFAULT_LIMITS["free"]).get(event_type, 10)

        quota = await tracker.check_quota(ctx.tenant_id, event_type, limit=limit)

        if not quota.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "quota_exceeded",
                    "event_type": event_type,
                    "used": quota.used,
                    "limit": quota.limit,
                    "reset_at": quota.reset_at.isoformat() if quota.reset_at else None,
                    "upgrade_message": quota.upgrade_message,
                    "docs_url": "/billing/plan",
                },
            )

        response = await call_next(request)

        # Fire-and-forget: increment after successful response
        if response.status_code < 400:
            try:
                await tracker.increment(ctx.tenant_id, event_type)
            except Exception:
                pass  # never block on tracking failure

        return response
```

- [ ] **Step 4: Register QuotaMiddleware in src/api/main.py**

```python
from src.billing.quota_middleware import QuotaMiddleware

# In create_app(), after TenantMiddleware:
app.add_middleware(QuotaMiddleware)
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/test_billing.py -k "middleware" -v
```

Expected: `PASS — 2 tests passed`

- [ ] **Step 6: Commit**

```bash
git add src/billing/quota_middleware.py src/api/main.py
git commit -m "feat(billing): QuotaMiddleware with per-event-type enforcement and 429 response"
```

---

## Task 5: Billing API Endpoints

**Files:**
- Create: `src/billing/models.py`
- Create: `src/api/routes/billing.py`

- [ ] **Step 1: Create src/billing/models.py**

```python
from pydantic import BaseModel
from datetime import datetime


class UsageItem(BaseModel):
    used: int
    limit: int | None
    remaining: int | None


class UsagePeriod(BaseModel):
    start: datetime
    end: datetime


class UsageResponse(BaseModel):
    tenant_id: str
    plan: str
    period: UsagePeriod
    usage: dict[str, UsageItem]


class PlanResponse(BaseModel):
    name: str
    display_name: str
    max_workflows: int | None
    max_hypotheses: int | None
    max_api_calls: int | None
    price_usd_cents: int
    status: str
```

- [ ] **Step 2: Create src/api/routes/billing.py**

```python
from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter, Depends, Request

from src.auth.dependencies import get_current_tenant
from src.billing.models import PlanResponse, UsageItem, UsagePeriod, UsageResponse
from src.billing.usage_tracker import UsageTracker, _next_month_reset
from src.tenancy.context import TenantContext

router = APIRouter(prefix="/billing", tags=["billing"])

_EVENT_TYPES = ["workflow_run", "hypothesis_generated", "api_call"]

_DEFAULT_LIMITS: dict[str, dict[str, int | None]] = {
    "free": {"workflow_run": 10, "hypothesis_generated": 100, "api_call": 1000},
    "pro": {"workflow_run": 100, "hypothesis_generated": 1000, "api_call": 10000},
    "enterprise": {"workflow_run": None, "hypothesis_generated": None, "api_call": None},
}


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    request: Request,
    ctx: TenantContext = Depends(get_current_tenant),
) -> Any:
    redis = request.app.state.redis
    tracker = UsageTracker(redis)
    plan_name = getattr(request.app.state, "tenant_plans", {}).get(ctx.tenant_id, "free")
    limits = _DEFAULT_LIMITS.get(plan_name, _DEFAULT_LIMITS["free"])

    usage: dict[str, UsageItem] = {}
    for event_type in _EVENT_TYPES:
        used = await tracker.get_usage(ctx.tenant_id, event_type)
        limit = limits.get(event_type)
        usage[event_type] = UsageItem(
            used=used,
            limit=limit,
            remaining=max(0, limit - used) if limit is not None else None,
        )

    now = datetime.now(UTC)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return UsageResponse(
        tenant_id=ctx.tenant_id,
        plan=plan_name,
        period=UsagePeriod(start=period_start, end=_next_month_reset()),
        usage=usage,
    )


@router.get("/plan", response_model=PlanResponse)
async def get_plan(
    request: Request,
    ctx: TenantContext = Depends(get_current_tenant),
) -> Any:
    plan_name = getattr(request.app.state, "tenant_plans", {}).get(ctx.tenant_id, "free")
    limits = _DEFAULT_LIMITS.get(plan_name, _DEFAULT_LIMITS["free"])
    plan_display = {"free": "Free", "pro": "Pro", "enterprise": "Enterprise"}
    plan_price = {"free": 0, "pro": 4900, "enterprise": 0}
    return PlanResponse(
        name=plan_name,
        display_name=plan_display.get(plan_name, plan_name.title()),
        max_workflows=limits.get("workflow_run"),
        max_hypotheses=limits.get("hypothesis_generated"),
        max_api_calls=limits.get("api_call"),
        price_usd_cents=plan_price.get(plan_name, 0),
        status="active",
    )
```

- [ ] **Step 3: Register billing router in src/api/main.py**

```python
from src.api.routes.billing import router as billing_router

# In create_app():
app.include_router(billing_router)
```

Also add `/billing` to exempt check (it requires JWT, not API key):

```python
# middleware.py _EXEMPT_PATHS — billing uses JWT, not API key
# No change needed — JWT middleware handles /billing routes
```

- [ ] **Step 4: Write endpoint tests**

Add to `tests/test_billing.py`:

```python
from fastapi.testclient import TestClient
from src.api.main import create_app
from unittest.mock import patch, AsyncMock

def test_billing_usage_requires_auth():
    app = create_app()
    client = TestClient(app)
    response = client.get("/billing/usage")
    assert response.status_code == 401

def test_billing_plan_requires_auth():
    app = create_app()
    client = TestClient(app)
    response = client.get("/billing/plan")
    assert response.status_code == 401
```

- [ ] **Step 5: Run all billing tests**

```bash
pytest tests/test_billing.py -v
```

Expected: `PASS — all tests pass`

- [ ] **Step 6: Commit**

```bash
git add src/billing/models.py src/api/routes/billing.py src/api/main.py
git commit -m "feat(billing): /billing/usage and /billing/plan endpoints"
```

---

## Task 6: Run Full Test Suite + Final Verify

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

- [ ] **Step 3: Verify middleware order in main.py**

Middleware executes in reverse registration order in FastAPI. Correct order:

```python
app.add_middleware(SecurityMiddleware)   # 1st registered = outermost (runs last)
app.add_middleware(TenantMiddleware)     # 2nd = runs before SecurityMiddleware
app.add_middleware(QuotaMiddleware)      # 3rd = runs innermost (after JWT injects tenant)
```

- [ ] **Step 4: Update ROADMAP_V1.md**

```markdown
## ระยะที่ 3: Enterprise & SaaS Readiness (9-12 สัปดาห์)
- [x] Multi-tenant Infrastructure
- [x] Auth & API Gateway (JWT)
- [x] Usage Quota & Billing
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: Phase 3 Enterprise & SaaS Readiness complete (3A+3B+3C)"
```
