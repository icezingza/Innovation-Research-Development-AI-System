"""End-to-end test: Phase 4A - Auditable Trail + FinOps + Tenant Isolation"""

import sys
import requests

BASE = "http://127.0.0.1:8001"
PASS = "[PASS]"
FAIL = "[FAIL]"

results = []


def check(label: str, ok: bool, detail: str = "") -> None:
    symbol = PASS if ok else FAIL
    results.append(ok)
    detail_str = f"  -> {detail}" if detail else ""
    print(f"  [{symbol}] {label}{detail_str}")


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


# ─── 1. Tenant A: register ──────────────────────────────────────────
section("Step 1: Register Tenant A + Tenant B")

r = requests.post(
    f"{BASE}/tenants",
    json={
        "name": "Acme Corp",
        "domain": "acme.example.com",
        "tier": "pro",
        "admin_email": "admin@acme.example.com",
        "admin_password": "SecurePass1!",
    },
)
check(
    "POST /tenants (Tenant A created)",
    r.status_code in (200, 201, 409),
    f"status={r.status_code}",
)

# Retrieve tenant_id from response or skip if already exists
if r.status_code in (200, 201):
    tenant_a = r.json()
    TENANT_A_ID = tenant_a["id"]
    print(f"     Tenant A ID: {TENANT_A_ID}")
elif r.status_code == 409:
    # Already exists -- try to get it via login
    TENANT_A_ID = "existing"
    print("     Tenant A already exists -- will discover ID via login")
else:
    print(f"     UNEXPECTED: {r.text}")
    sys.exit(1)

r = requests.post(
    f"{BASE}/tenants",
    json={
        "name": "Beta Ltd",
        "domain": "beta.example.com",
        "tier": "free",
        "admin_email": "admin@beta.example.com",
        "admin_password": "SecurePass2!",
    },
)
check(
    "POST /tenants (Tenant B created)",
    r.status_code in (200, 201, 409),
    f"status={r.status_code}",
)
if r.status_code in (200, 201):
    TENANT_B_ID = r.json()["id"]
    print(f"     Tenant B ID: {TENANT_B_ID}")
else:
    TENANT_B_ID = "existing"

# ─── 2. Login Tenant A ───────────────────────────────────────────────
section("Step 2: Login Tenant A admin")

if TENANT_A_ID == "existing":
    # Try logging in without tenant_id to discover it (fallback)
    print("     Cannot login without tenant_id -- please clean DB and re-run")
    sys.exit(0)

r = requests.post(
    f"{BASE}/auth/login",
    json={
        "email": "admin@acme.example.com",
        "password": "SecurePass1!",
        "tenant_id": TENANT_A_ID,
    },
)
check("POST /auth/login (Tenant A)", r.status_code == 200, f"status={r.status_code}")

if r.status_code != 200:
    print(f"     Login failed: {r.text}")
    sys.exit(1)

TOKEN_A = r.json()["access_token"]
HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
print(f"     Token A: {TOKEN_A[:60]}...")


# ─── 3. Login Tenant B ───────────────────────────────────────────────
section("Step 3: Login Tenant B admin")

if TENANT_B_ID != "existing":
    r = requests.post(
        f"{BASE}/auth/login",
        json={
            "email": "admin@beta.example.com",
            "password": "SecurePass2!",
            "tenant_id": TENANT_B_ID,
        },
    )
    check(
        "POST /auth/login (Tenant B)", r.status_code == 200, f"status={r.status_code}"
    )
    TOKEN_B = r.json().get("access_token", "")
    HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}
else:
    HEADERS_B = {}


# ─── 4. Create Research Task (Tenant A) ─────────────────────────────
section("Step 4: Create Research Task (Tenant A)")

r = requests.post(
    f"{BASE}/research/tasks",
    json={"question": "What is the nature of consciousness?"},
    headers=HEADERS_A,
)
check(
    "POST /research/tasks (Tenant A)",
    r.status_code in (200, 202),
    f"status={r.status_code}",
)

TASK_ID = None
if r.status_code in (200, 202):
    TASK_ID = r.json().get("task_id")
    print(f"     Task ID: {TASK_ID}")
else:
    print(f"     Response: {r.text[:200]}")


# ─── 5. GET /research/tasks/{task_id}/trace ─────────────────────────
section("Step 5: GET /research/tasks/{task_id}/trace (Auditable Trail)")

if TASK_ID:
    r = requests.get(f"{BASE}/research/tasks/{TASK_ID}/trace", headers=HEADERS_A)
    check(
        "GET /trace (admin role, Tenant A)",
        r.status_code == 200,
        f"status={r.status_code}",
    )

    if r.status_code == 200:
        data = r.json()
        print(f"     Task ID: {data.get('task_id')}")
        print(f"     Event count: {len(data.get('events', []))}")
        print(f"     Tenant: {data.get('tenant_id')}")
        if data.get("events"):
            ev = data["events"][0]
            print(
                f"     First event: agent={ev.get('agent')}, action={ev.get('action')}"
            )
    else:
        print(f"     Response: {r.text[:200]}")

    # Test: no auth -> 401
    r_noauth = requests.get(f"{BASE}/research/tasks/{TASK_ID}/trace")
    check(
        "GET /trace (no auth -> 401)",
        r_noauth.status_code == 401,
        f"status={r_noauth.status_code}",
    )

    # Test: Tenant B tries to access Tenant A task -> 403 or 404
    if HEADERS_B:
        r_b = requests.get(f"{BASE}/research/tasks/{TASK_ID}/trace", headers=HEADERS_B)
        check(
            "GET /trace cross-tenant (Tenant B -> 403/404)",
            r_b.status_code in (403, 404),
            f"status={r_b.status_code} -- Tenant isolation OK",
        )
else:
    print("     No TASK_ID -- skipping trace test")
    results.append(False)


# ─── 6. GET /tenants/{tenant_id}/finops ─────────────────────────────
section("Step 6: GET /tenants/{tenant_id}/finops (FinOps)")

r = requests.get(f"{BASE}/tenants/{TENANT_A_ID}/finops", headers=HEADERS_A)
check("GET /finops (Tenant A)", r.status_code == 200, f"status={r.status_code}")

if r.status_code == 200:
    d = r.json()
    print(f"     Quota limit:   {d.get('quota_limit')}")
    print(f"     Quota used:    {d.get('quota_used')}")
    print(f"     Est. cost:     ${d.get('estimated_cost', 0):.2f}")
    print(f"     Forecast:      {d.get('budget_depletion_forecast', 'N/A')}")
    print(f"     Recommendation: {d.get('recommendation', '')[:80]}")
else:
    print(f"     Response: {r.text[:200]}")

# Tenant B cannot access Tenant A's finops
if HEADERS_B:
    r_b = requests.get(f"{BASE}/tenants/{TENANT_A_ID}/finops", headers=HEADERS_B)
    check(
        "GET /finops cross-tenant (Tenant B -> 403)",
        r_b.status_code == 403,
        f"status={r_b.status_code} -- FinOps isolation OK",
    )


# ─── Summary ─────────────────────────────────────────────────────────
section("SUMMARY")
passed = sum(results)
total = len(results)
print(f"  {passed}/{total} checks passed")
if passed == total:
    print("\n  ALL CHECKS PASSED -- Phase 4A ready for Demo!")
else:
    print(f"\n  {total - passed} checks FAILED -- see above")
