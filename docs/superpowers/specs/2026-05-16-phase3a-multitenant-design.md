# Phase 3A Design Spec — Multi-tenant Infrastructure

**Date:** 2026-05-16  
**Author:** Namo (AI Project Leader)  
**Status:** Approved  

---

## 1. Objective

Add multi-tenant isolation to the IRD-AI system so multiple organizations can use the platform independently with full data separation. Each tenant's workflows, hypotheses, reasoning traces, and sessions are invisible to other tenants.

**Success criterion:** Two tenants can run concurrent workflows and never see each other's data.

---

## 2. Tenant Model: Hybrid (Org + User + Role)

```
Tenant (org)
  ├── User A  [role: owner]
  ├── User B  [role: admin]
  └── User C  [role: member]
```

- **Tenant** = an organization (company, research team)
- **User** = individual login identity
- **TenantMember** = junction table (user ↔ tenant + role)
- One user can belong to multiple tenants
- Role enum: `owner | admin | member`

---

## 3. Isolation Strategy: Row-Level (tenant_id FK)

All existing tables get a `tenant_id` column (FK → tenants.id, NOT NULL after migration).

```sql
-- Added to: workflow_records, hypothesis_records, reasoning_traces, research_tasks
tenant_id UUID NOT NULL REFERENCES tenants(id)
```

A **system tenant** (`id = '00000000-0000-0000-0000-000000000001'`) is seeded at migration time — existing rows are assigned to it for backward compatibility.

---

## 4. New Tables

### tenants
```sql
id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
name        VARCHAR(255) NOT NULL
slug        VARCHAR(100) UNIQUE NOT NULL  -- URL-safe identifier
plan        VARCHAR(50) DEFAULT 'free'   -- free | pro | enterprise
is_active   BOOLEAN DEFAULT true
created_at  TIMESTAMPTZ DEFAULT now()
```

### users
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
email           VARCHAR(255) UNIQUE NOT NULL
hashed_password VARCHAR(255) NOT NULL
display_name    VARCHAR(255)
is_active       BOOLEAN DEFAULT true
created_at      TIMESTAMPTZ DEFAULT now()
last_login_at   TIMESTAMPTZ
```

### tenant_members
```sql
id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE
user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
role        VARCHAR(50) NOT NULL DEFAULT 'member'  -- owner | admin | member
joined_at   TIMESTAMPTZ DEFAULT now()
UNIQUE(tenant_id, user_id)
```

---

## 5. Schema Updates (Existing Tables)

```
workflow_records    → ADD tenant_id UUID NOT NULL
hypothesis_records  → ADD tenant_id UUID NOT NULL
reasoning_traces    → ADD tenant_id UUID NOT NULL
research_tasks      → ADD tenant_id UUID NOT NULL
```

Indexes added: `ix_workflow_tenant`, `ix_hypothesis_tenant`, `ix_reasoning_tenant`, `ix_research_task_tenant`

---

## 6. Alembic Migrations

- **002_tenant_schema.py** — Create `tenants`, `users`, `tenant_members` tables + seed system tenant
- **003_add_tenant_id.py** — Add `tenant_id` to all existing tables (nullable first → backfill → NOT NULL)

Two-step approach for `tenant_id` (nullable → backfill → not null) avoids locking issues on existing data.

---

## 7. TenantContext

A lightweight context object passed through the request lifecycle:

```python
@dataclass
class TenantContext:
    tenant_id: str
    user_id: str
    role: str  # owner | admin | member
```

Stored in `request.state.tenant` by middleware (Phase 3B wires this via JWT). For Phase 3A, a dev header `X-Tenant-ID` is used to test isolation before JWT is ready.

---

## 8. ResearchMemory + Query Scoping

All database queries in `src/memory/` that read/write `HypothesisRecord`, `WorkflowRecord`, `ReasoningTraceRecord` must be updated to filter by `tenant_id`.

Pattern: every query receives `tenant_id: str` parameter and applies `.where(Table.tenant_id == tenant_id)`.

---

## 9. Out of Scope (Phase 3A)

- JWT auth (Phase 3B)
- Quota enforcement (Phase 3C)
- Tenant admin UI
- Tenant invite/onboarding flow
