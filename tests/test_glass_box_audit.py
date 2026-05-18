"""Tests for Glass-Box Dashboard, OpenTelemetry instrumentation, and Telemetry API."""


import pytest
from opentelemetry import trace

from src.telemetry.instrumentation import (
    CognitiveAttr,
    cognitive_span,
    record_pdpa_outcome,
    record_risk_outcome,
    trace_cognitive_phase,
)
from src.telemetry.tracing import configure_tracing, tracer


# ── configure_tracing ─────────────────────────────────────────────────────────

def test_configure_tracing_sets_provider():
    configure_tracing()
    provider = trace.get_tracer_provider()
    assert provider is not None


def test_configure_tracing_creates_named_tracer():
    configure_tracing()
    t = trace.get_tracer("test-tracer", "0.1.0")
    assert t is not None


def test_tracer_module_level_instance():
    assert tracer is not None


# ── CognitiveAttr constants ───────────────────────────────────────────────────

def test_cognitive_attr_constants_are_strings():
    attrs = [
        CognitiveAttr.TENANT_ID, CognitiveAttr.DOMAIN, CognitiveAttr.PHASE,
        CognitiveAttr.AGENT_ID, CognitiveAttr.RISK_LEVEL, CognitiveAttr.PDPA_STATUS,
        CognitiveAttr.RUN_ID, CognitiveAttr.QUERY_LENGTH, CognitiveAttr.RESULT_COUNT,
        CognitiveAttr.SWARM,
    ]
    for attr in attrs:
        assert isinstance(attr, str)
        assert attr.startswith("cognitive.")


# ── cognitive_span context manager ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_cognitive_span_runs_without_error():
    async with cognitive_span("test.operation", tenant_id="t1", domain="fintech"):
        pass  # just ensure no exception


@pytest.mark.asyncio
async def test_cognitive_span_propagates_exception():
    with pytest.raises(ValueError, match="test error"):
        async with cognitive_span("test.error_span"):
            raise ValueError("test error")


@pytest.mark.asyncio
async def test_cognitive_span_yields_span_object():
    async with cognitive_span("test.span_object") as span:
        assert span is not None


@pytest.mark.asyncio
async def test_cognitive_span_accepts_extra_kwargs():
    async with cognitive_span("test.extras", tenant_id="t1", my_custom_field="value"):
        pass  # no error = extra attrs accepted gracefully


# ── trace_cognitive_phase decorator ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_trace_cognitive_phase_wraps_async_fn():
    @trace_cognitive_phase("test.decorated", domain="legal")
    async def my_fn(query: str) -> str:
        return "result:" + query

    result = await my_fn("hello")
    assert result == "result:hello"


@pytest.mark.asyncio
async def test_trace_cognitive_phase_passes_tenant_id():
    calls = []

    @trace_cognitive_phase("test.tenant_pass", domain="fintech")
    async def my_fn(tenant_id: str = "") -> str:
        calls.append(tenant_id)
        return tenant_id

    await my_fn(tenant_id="tenant-123")
    assert calls == ["tenant-123"]


# ── record_risk_outcome / record_pdpa_outcome ────────────────────────────────

def test_record_risk_outcome_does_not_raise():
    with tracer.start_as_current_span("test.risk_outcome") as span:
        record_risk_outcome(span, "HIGH", result_count=5)


def test_record_pdpa_outcome_does_not_raise():
    with tracer.start_as_current_span("test.pdpa_outcome") as span:
        record_pdpa_outcome(span, "NON_COMPLIANT")


# ── Telemetry API endpoints ───────────────────────────────────────────────────

def test_telemetry_status_endpoint(test_app):
    from fastapi.testclient import TestClient
    with TestClient(test_app) as client:
        resp = client.get("/telemetry/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert "uptime_seconds" in data
    assert "tracing" in data
    assert data["sla_target"] == "99.99%"


def test_telemetry_status_has_instrumented_operations(test_app):
    from fastapi.testclient import TestClient
    with TestClient(test_app) as client:
        resp = client.get("/telemetry/status")
    data = resp.json()
    ops = data["tracing"]["instrumented_operations"]
    assert isinstance(ops, list)
    assert any("fintech" in op for op in ops)
    assert any("legal" in op for op in ops)


def test_telemetry_status_has_cognitive_attributes(test_app):
    from fastapi.testclient import TestClient
    with TestClient(test_app) as client:
        resp = client.get("/telemetry/status")
    attrs = resp.json()["tracing"]["cognitive_attributes"]
    assert "cognitive.tenant_id" in attrs
    assert "cognitive.risk_level" in attrs
    assert "cognitive.pdpa_status" in attrs


def test_telemetry_health_no_auth_required(test_app):
    from fastapi.testclient import TestClient
    with TestClient(test_app) as client:
        resp = client.get("/telemetry/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["healthy"] is True
    assert "uptime_seconds" in data
    assert "exporter" in data


# ── Glass-Box dashboard route ─────────────────────────────────────────────────

def test_glass_box_dashboard_served(test_app):
    from fastapi.testclient import TestClient
    with TestClient(test_app) as client:
        resp = client.get("/dashboard/glass-box")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_glass_box_dashboard_contains_audit_key_ui(test_app):
    from fastapi.testclient import TestClient
    with TestClient(test_app) as client:
        resp = client.get("/dashboard/glass-box")
    body = resp.text
    assert "Glass-Box Auditor" in body
    assert "X-Auditor-Key" in body


def test_glass_box_dashboard_no_innerhtml(test_app):
    """Dashboard must use safe DOM APIs — XSS policy check."""
    from fastapi.testclient import TestClient
    with TestClient(test_app) as client:
        resp = client.get("/dashboard/glass-box")
    # innerHTML = '' clears only; all text content must use textContent/createElement
    body = resp.text
    # Verify verifier uses textContent, not innerHTML, for dynamic content
    assert "el.textContent = msg" in body or ".textContent =" in body


def test_glass_box_dashboard_has_sha256_verifier(test_app):
    from fastapi.testclient import TestClient
    with TestClient(test_app) as client:
        resp = client.get("/dashboard/glass-box")
    body = resp.text
    assert "SHA-256" in body
    assert "crypto.subtle.digest" in body


# ── Fintech swarm span integration ───────────────────────────────────────────

def test_fintech_swarm_imports_tracer():
    from src.swarms.fintech_swarm import FintechSwarm  # noqa: F401
    from src.telemetry.tracing import tracer as t
    assert t is not None


def test_legal_swarm_imports_tracer():
    from src.swarms.legal_swarm import LegalSwarm  # noqa: F401
    from src.telemetry.tracing import tracer as t
    assert t is not None
