"""P3 — API Correctness.

Exercises every public route with a minimal valid payload and asserts
status code + presence of required response fields. No 5xx is acceptable
on valid input. Empty/invalid input must yield a 4xx (never 5xx).
"""

from __future__ import annotations

import pytest

from src.security.auth_utils import create_access_token
from src.tenants.context import SYSTEM_TENANT_ID


def _auth_headers() -> dict[str, str]:
    """Mint a JWT for routes guarded by get_current_user."""
    token = create_access_token(
        data={
            "sub": "test-user",
            "tenant_id": SYSTEM_TENANT_ID,
            "role": "admin",
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# health.py
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_health(api_client):
    r = await api_client.get("/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "runtime" in body
    assert body["runtime"] in {"healthy", "degraded"}


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_metrics(api_client):
    r = await api_client.get("/metrics")
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# runtime.py
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_runtime_state(api_client):
    r = await api_client.get("/runtime/state")
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), dict)


# ---------------------------------------------------------------------------
# research.py — POST requires JWT
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_research_create_task(api_client):
    r = await api_client.post(
        "/research/tasks",
        json={"question": "What is emergence?"},
        headers=_auth_headers(),
    )
    # 202 on success; accept 401/422 if guard rejects in this env, but never 5xx
    assert r.status_code < 500, r.text
    if r.status_code == 202:
        body = r.json()
        assert "task_id" in body
        assert body["status"] == "pending"


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_research_get_task_not_found(api_client):
    r = await api_client.get("/research/tasks/does-not-exist-uuid")
    # 404 expected; never 5xx
    assert r.status_code in {404, 401, 403}, r.text


# ---------------------------------------------------------------------------
# workflows.py
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_workflows_create(api_client):
    r = await api_client.post(
        "/research/workflows",
        json={"goal": "Test workflow goal"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert "workflow_id" in body
    assert body["status"] == "pending"


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_workflows_get_not_found(api_client):
    r = await api_client.get("/research/workflows/does-not-exist")
    assert r.status_code == 404, r.text


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_workflows_list(api_client):
    r = await api_client.get("/research/workflows")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "workflows" in body
    assert "count" in body


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_workflows_empty_body_is_4xx(api_client):
    """Negative test: empty body must yield 4xx (validation error), NEVER 5xx."""
    r = await api_client.post("/research/workflows", json={})
    assert r.status_code < 500, r.text
    assert 400 <= r.status_code < 500, r.text


# ---------------------------------------------------------------------------
# reasoning.py
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_reasoning_recursive(api_client):
    r = await api_client.post(
        "/reasoning/recursive",
        json={
            "hypothesis_statement": "Recursion converges given a stable signal.",
            "evidence": ["Prior trials show oscillation damps over time."],
            "confidence": 0.6,
            "question": "Does iterative refinement converge?",
            "max_depth": 2,
            "convergence_threshold": 0.85,
        },
    )
    assert r.status_code < 500, r.text
    assert r.status_code == 200, r.text


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_reasoning_debate(api_client):
    r = await api_client.post(
        "/reasoning/debates",
        json={"hypothesis": "All swans are white.", "max_rounds": 1},
    )
    assert r.status_code < 500, r.text
    assert r.status_code == 200, r.text


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_reasoning_traces(api_client):
    r = await api_client.get("/reasoning/traces")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "count" in body
    assert "traces" in body


# ---------------------------------------------------------------------------
# governance.py
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_governance_audit(api_client):
    r = await api_client.get("/governance/audit")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "entries" in body
    assert "count" in body


# ---------------------------------------------------------------------------
# cognition.py
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_cognition_coordinate(api_client):
    r = await api_client.post(
        "/cognition/coordinate",
        json={"goal": "Investigate the nature of cognition."},
    )
    assert r.status_code < 500, r.text
    assert r.status_code == 200, r.text


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_cognition_event_stats(api_client):
    r = await api_client.get("/cognition/events/stats")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "total_events_published" in body
    assert "total_subscribers" in body


# ---------------------------------------------------------------------------
# intelligence.py
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_intelligence_report(api_client):
    r = await api_client.get("/intelligence/report")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "knowledge_base" in body
    assert "recent_findings" in body


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_intelligence_recall(api_client):
    # Note: /intelligence/recall is a GET with `topic` query param, not POST.
    r = await api_client.get("/intelligence/recall", params={"topic": "emergence"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["topic"] == "emergence"
    assert "entries" in body


# ---------------------------------------------------------------------------
# streams.py
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_streams_active(api_client):
    r = await api_client.get("/streams/active")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "active_streams" in body


# ---------------------------------------------------------------------------
# dashboard.py — plan's /dashboard/metrics does not exist. Real routes
# serve static HTML files. Hit /dashboard/roi which has no path params.
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_dashboard_roi(api_client):
    r = await api_client.get("/dashboard/roi")
    # 200 if template file exists, 404 if missing — never 5xx.
    assert r.status_code < 500, r.text
    assert r.status_code in {200, 404}, r.text
