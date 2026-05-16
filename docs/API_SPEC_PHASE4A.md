# 📡 Phase 4A API Specification

## 1. Auditable AI Trail
### GET /research/tasks/{task_id}/trace
- **Authorization:** Bearer JWT (role=admin|auditor)
- **Response 200:**
```json
{
  "task_id": "uuid",
  "events": [
    {
      "timestamp": "2026-05-16T10:00:00Z",
      "agent": "HypothesisAgent",
      "action": "propose",
      "content": {"hypothesis": "..."}
    },
    {
      "timestamp": "2026-05-16T10:01:00Z",
      "agent": "ResearchAgent",
      "action": "search",
      "content": {"query": "...", "results": 12}
    },
    {
      "timestamp": "2026-05-16T10:02:00Z",
      "agent": "CritiqueAgent",
      "action": "refute",
      "content": {"reason": "..."}
    },
    {
      "timestamp": "2026-05-16T10:03:00Z",
      "agent": "SynthesisAgent",
      "action": "finalize",
      "content": {"summary": "..."}
    }
  ]
}
```

- **Error 403:** Role ไม่ได้รับอนุญาต  
- **Error 404:** Task not found in this tenant

---

## 2. Cognitive FinOps API
### GET /tenants/{tenant_id}/finops
- **Authorization:** Bearer JWT (role=admin|finance)
- **Response 200:**

```json
{
  "tenant_id": "uuid",
  "current_billing_period": "2026-05",
  "quota_limit": 50000,
  "quota_used": 12453,
  "estimated_cost": 124.53,
  "budget_depletion_forecast": "2026-05-28T15:00:00Z",
  "recommendation": "At current rate, budget will last 12 more days. Consider upgrading to Pro."
}
```

- **Headers:** `X-Quota-Used`, `X-Quota-Limit`

---

## 3. ROI Analytics (Phase 4C preview)
### GET /tenants/{tenant_id}/roi
- **Authorization:** Bearer JWT (role=admin)
- **Response 200:**

```json
{
  "tenant_id": "uuid",
  "period": "2026-05",
  "hours_saved": 340,
  "token_cost_cloud_equivalent": 1500.00,
  "actual_token_cost": 124.53,
  "savings_percentage": 91.7,
  "tasks_completed": 128,
  "avg_time_per_task_seconds": 45
}
```

---

*API ทั้งหมดอยู่ภายใต้ Rate Limiting และ Quota Enforcement เดียวกับระบบหลัก*
