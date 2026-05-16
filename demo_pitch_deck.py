"""Pitch Deck Demo Script — NamoNexus Phase 4 (6 Moats)
=========================================================
ใช้สำหรับ capture screenshots สำหรับนักลงทุน

วิธีใช้:
  1. ตรวจว่า uvicorn รันอยู่ port 8004 (curl http://127.0.0.1:8004/health)
  2. รันสคริปต์นี้: python demo_pitch_deck.py
  3. ทำตามลำดับ screenshot ที่สคริปต์บอก
  4. JWT token + URLs จะถูก print + save ใน demo_artifacts/

Audience priority: B (Business) > A (Technical Depth) > C (Security)
"""
import json
import time
import webbrowser
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8009"
ARTIFACTS = Path(__file__).parent / "demo_artifacts"
ARTIFACTS.mkdir(exist_ok=True)


def banner(title: str) -> None:
    print(f"\n{'='*70}\n  {title}\n{'='*70}")


def pause(prompt: str = "Press ENTER after capturing screenshot...") -> None:
    try:
        input(f"\n>>> {prompt}")
    except EOFError:
        pass  # non-interactive mode (CI/script)


# ─── Step 0: Health check ───────────────────────────────────────────
banner("Step 0: Verify server is running")
r = requests.get(f"{BASE}/health")
assert r.status_code == 200, f"Server not healthy: {r.text}"
print(f"  [OK] {r.json()}")


# ─── Step 1: Provision Tenant A (Acme) + B (Beta) ───────────────────
banner("Step 1: Provision tenants (demo data)")
ts = int(time.time())
DOMAIN_A = f"acme-{ts}.demo"
DOMAIN_B = f"beta-{ts}.demo"
EMAIL_A = f"admin@{DOMAIN_A}"
EMAIL_B = f"admin@{DOMAIN_B}"
PWD = "DemoPass2026!"

r = requests.post(f"{BASE}/tenants", json={
    "name": "Acme Corp",
    "domain": DOMAIN_A,
    "tier": "pro",
    "admin_email": EMAIL_A,
    "admin_password": PWD,
})
assert r.status_code == 201, f"Tenant A creation failed: {r.text}"
TENANT_A_ID = r.json()["id"]
print(f"  [OK] Tenant A (Acme, Pro tier): {TENANT_A_ID}")

r = requests.post(f"{BASE}/tenants", json={
    "name": "Beta Ltd",
    "domain": DOMAIN_B,
    "tier": "free",
    "admin_email": EMAIL_B,
    "admin_password": PWD,
})
assert r.status_code == 201, f"Tenant B creation failed: {r.text}"
TENANT_B_ID = r.json()["id"]
print(f"  [OK] Tenant B (Beta, Free tier): {TENANT_B_ID}")


# ─── Step 2: Login + get JWTs ───────────────────────────────────────
banner("Step 2: Login both tenants -> JWT tokens")

r = requests.post(f"{BASE}/auth/login", json={
    "email": EMAIL_A, "password": PWD, "tenant_id": TENANT_A_ID,
})
TOKEN_A = r.json()["access_token"]
print(f"  [OK] Token A: {TOKEN_A[:60]}...")

r = requests.post(f"{BASE}/auth/login", json={
    "email": EMAIL_B, "password": PWD, "tenant_id": TENANT_B_ID,
})
TOKEN_B = r.json()["access_token"]
print(f"  [OK] Token B: {TOKEN_B[:60]}...")


# ─── Step 3: Create research task (Tenant A) ────────────────────────
banner("Step 3: Create Research Task -> populate audit trail")
r = requests.post(
    f"{BASE}/research/tasks",
    json={"question": "How can AI reduce hospital readmission rates in Thailand?"},
    headers={"Authorization": f"Bearer {TOKEN_A}"},
)
print(f"  Status: {r.status_code}")
TASK_ID = r.json().get("task_id") if r.status_code in (200, 202) else "no-task"
print(f"  [OK] Task ID: {TASK_ID}")

# Wait for background agents to populate trace
print("  Waiting 3s for background agents...")
time.sleep(3)


# ─── Save artifacts ─────────────────────────────────────────────────
artifacts = {
    "tenant_a": {"id": TENANT_A_ID, "domain": DOMAIN_A, "email": EMAIL_A, "tier": "pro"},
    "tenant_b": {"id": TENANT_B_ID, "domain": DOMAIN_B, "email": EMAIL_B, "tier": "free"},
    "token_a": TOKEN_A,
    "token_b": TOKEN_B,
    "task_id": TASK_ID,
    "base_url": BASE,
}
(ARTIFACTS / "demo_session.json").write_text(json.dumps(artifacts, indent=2))
print(f"\n  Artifacts saved to: {ARTIFACTS / 'demo_session.json'}")


# ─── Print URLs for each screenshot ─────────────────────────────────
banner("SCREENSHOT CAPTURE GUIDE — 5 screens for Pitch Deck")

screenshots = [
    {
        "n": 1,
        "title": "FinOps Dashboard (CFO view)",
        "url": f"{BASE}/dashboard/finops/{TENANT_A_ID}",
        "tip": "เปิด Browser DevTools (F12) -> Application -> Local Storage -> "
               f"add key='token' value='{TOKEN_A[:30]}...' -> reload page",
        "selling_point": "CFO เห็นต้นทุน AI + Forecast ใน 3 วิ",
    },
    {
        "n": 2,
        "title": "ROI Dashboard (Business case)",
        "url": f"{BASE}/dashboard/roi?tenant_id={TENANT_A_ID}",
        "tip": "Capture pie chart + 'Hours Saved' big number",
        "selling_point": "พิสูจน์ ROI 60-80% เทียบกับ cloud AI services",
    },
    {
        "n": 3,
        "title": "Audit Trail Timeline (CTO view)",
        "url": f"{BASE}/dashboard/trace/{TASK_ID}",
        "tip": "เห็น timeline: Hypothesis -> Research -> Critique -> Synthesis",
        "selling_point": "Technical depth — every AI decision is auditable",
    },
    {
        "n": 4,
        "title": "Swagger UI — API Coverage",
        "url": f"{BASE}/docs",
        "tip": "Scroll ไปที่ /research/tasks/{task_id}/trace, คลิก 'Try it out' "
               "-> ใส่ JWT ใน Authorize button -> ดู JSON response",
        "selling_point": "Production-grade API — fully documented",
    },
    {
        "n": 5,
        "title": "Security Isolation Proof (Tenant B -> 403)",
        "url": "Terminal screenshot of curl command",
        "tip": (
            f"\nรันใน Terminal/PowerShell:\n"
            f"  curl -i -H \"Authorization: Bearer {TOKEN_B[:40]}...\" "
            f"\\\n       {BASE}/tenants/{TENANT_A_ID}/finops\n"
            f"  # Expected: HTTP/1.1 403 Forbidden"
        ),
        "selling_point": "Multi-tenant isolation enforced at API layer",
    },
]

for s in screenshots:
    print(f"\n  [{s['n']}/5] {s['title']}")
    print(f"        URL: {s['url']}")
    print(f"        Tip: {s['tip']}")
    print(f"        Sell: {s['selling_point']}")

# Print the JWT injection helper for browser
banner("BROWSER JWT INJECTION SNIPPET (paste in DevTools Console)")
print(f"""
  // Paste in browser console (F12 -> Console tab) before reloading dashboard:
  localStorage.setItem('token', '{TOKEN_A}');
  localStorage.setItem('access_token', '{TOKEN_A}');
  location.reload();
""")

banner("READY — Capture screenshots in this order:")
print("""
  1. FinOps  -> save as: pitch_01_finops.png
  2. ROI     -> save as: pitch_02_roi.png
  3. Trace   -> save as: pitch_03_audit_trail.png
  4. Swagger -> save as: pitch_04_api_docs.png
  5. cURL    -> save as: pitch_05_isolation_proof.png

  Save all 5 PNGs into:  demo_artifacts/screenshots/

  Then drop them into Pitch Deck slides 8-12.
""")

# Auto-open first dashboard in default browser
print("\nOpening FinOps dashboard in browser...")
webbrowser.open(screenshots[0]["url"])
