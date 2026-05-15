# Phase 3C Design Spec — Usage Quota & Billing

**Date:** 2026-05-16  
**Author:** Namo (AI Project Leader)  
**Status:** Approved  
**Depends on:** Phase 3A (tenant schema), Phase 3B (JWT auth)

---

## 1. Objective

Enforce per-tenant usage quotas based on subscription tier, record usage events for billing, and provide a usage API for the dashboard. No payment processing in Phase 3 — Stripe integration is Phase 4.

**Success criterion:** A Free-tier tenant hitting their workflow limit gets a 429 with a clear upgrade message. Usage is tracked accurately per tenant per month.

---

## 2. Subscription Tiers

| Tier | Workflows/month | Hypotheses/month | API calls/month | Price |
|---|---|---|---|---|
| **free** | 10 | 100 | 1,000 | $0 |
| **pro** | 100 | 1,000 | 10,000 | $49/mo |
| **enterprise** | unlimited | unlimited | unlimited | Custom |

---

## 3. New Tables

### subscription_plans
```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
name             VARCHAR(50) UNIQUE NOT NULL   -- free | pro | enterprise
display_name     VARCHAR(100) NOT NULL
max_workflows    INTEGER   -- NULL = unlimited
max_hypotheses   INTEGER   -- NULL = unlimited
max_api_calls    INTEGER   -- NULL = unlimited
price_usd_cents  INTEGER NOT NULL DEFAULT 0
created_at       TIMESTAMPTZ DEFAULT now()
```

### tenant_subscriptions
```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
tenant_id        UUID UNIQUE NOT NULL REFERENCES tenants(id)
plan_id          UUID NOT NULL REFERENCES subscription_plans(id)
status           VARCHAR(50) DEFAULT 'active'  -- active | cancelled | past_due
current_period_start  TIMESTAMPTZ NOT NULL
current_period_end    TIMESTAMPTZ NOT NULL
created_at       TIMESTAMPTZ DEFAULT now()
updated_at       TIMESTAMPTZ DEFAULT now()
```

### usage_events
```sql
id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
tenant_id   UUID NOT NULL REFERENCES tenants(id)
user_id     UUID NOT NULL REFERENCES users(id)
event_type  VARCHAR(100) NOT NULL  -- workflow_run | hypothesis_generated | api_call
resource_id VARCHAR(255)           -- workflow_id, hypothesis_id, etc.
recorded_at TIMESTAMPTZ DEFAULT now()
INDEX: ix_usage_tenant_period (tenant_id, recorded_at)
```

---

## 4. UsageTracker

Async service that records events via EventBus (fire-and-forget, never blocks requests):

```python
class UsageTracker:
    async def record(self, tenant_id: str, user_id: str, event_type: str, resource_id: str | None = None) -> None
    async def get_current_usage(self, tenant_id: str) -> UsageSummary
    async def check_quota(self, tenant_id: str, event_type: str) -> QuotaStatus
```

### QuotaStatus
```python
@dataclass
class QuotaStatus:
    allowed: bool
    limit: int | None         # None = unlimited
    used: int
    remaining: int | None
    reset_at: datetime
    upgrade_message: str | None
```

---

## 5. Quota Enforcement Middleware

`QuotaMiddleware` runs after `JWTMiddleware` (has access to `request.state.tenant`):

```
Quota-checked paths:
  POST /research/workflows     → check workflow_run quota
  POST /reasoning/*            → check api_call quota
  POST /cognition/*            → check api_call quota

Enforcement flow:
1. Get tenant_id from request.state.tenant
2. Get current period usage from Redis cache (TTL: 60s)
3. Compare against plan limits
4. If over limit: return 429 { error: "quota_exceeded", upgrade_message, reset_at }
5. If allowed: call_next(request)
6. After response: publish UsageEvent to EventBus (async, non-blocking)
```

Redis cache key: `quota:{tenant_id}:{event_type}:{YYYY-MM}` → count (TTL: 1 hour)

---

## 6. New API Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/billing/usage` | Current period usage summary | Yes |
| GET | `/billing/plan` | Current subscription plan | Yes |
| GET | `/billing/history` | Usage history (last 3 months) | Yes (admin+) |

### GET /billing/usage Response
```json
{
  "tenant_id": "...",
  "plan": "pro",
  "period": { "start": "2026-05-01", "end": "2026-05-31" },
  "usage": {
    "workflows": { "used": 23, "limit": 100, "remaining": 77 },
    "hypotheses": { "used": 341, "limit": 1000, "remaining": 659 },
    "api_calls": { "used": 1204, "limit": 10000, "remaining": 8796 }
  }
}
```

---

## 7. File Structure

```
src/
├── billing/
│   ├── usage_tracker.py    ← UsageTracker, QuotaStatus, UsageSummary
│   ├── quota_middleware.py ← QuotaMiddleware (FastAPI BaseHTTPMiddleware)
│   └── models.py           ← Pydantic schemas for billing API
├── api/
│   └── routes/
│       └── billing.py      ← /billing/* endpoints
```

---

## 8. Alembic Migration

- **004_quota_billing.py** — Create `subscription_plans`, `tenant_subscriptions`, `usage_events` tables + seed default plans

---

## 9. 429 Response Format

```json
{
  "error": "quota_exceeded",
  "event_type": "workflow_run",
  "used": 10,
  "limit": 10,
  "reset_at": "2026-06-01T00:00:00Z",
  "upgrade_message": "Upgrade to Pro for 100 workflows/month. Contact sales@ird-ai.com",
  "docs_url": "/billing/plan"
}
```

---

## 10. Out of Scope (Phase 3C)

- Stripe payment integration (Phase 4)
- Invoice generation
- Proration on plan change
- Usage alerts/notifications
- Admin billing dashboard
