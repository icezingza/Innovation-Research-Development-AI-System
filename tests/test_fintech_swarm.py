"""Tests for FintechKnowledgeRetriever and FintechSwarm."""

import hashlib
import json

from src.agents.subagents.fintech_retriever import FintechKnowledgeRetriever
from src.swarms.fintech_swarm import FintechSwarm


# ── FintechKnowledgeRetriever unit tests ─────────────────────────────────────


async def _run_retriever(query: str, tx: dict | None = None) -> dict:
    retriever = FintechKnowledgeRetriever()
    result = None
    async for chunk in retriever.execute(
        {"query": query, "transaction_data": tx or {}}
    ):
        if chunk.get("status") == "completed":
            result = chunk["insight"]
    return result or {}


def test_retriever_returns_risk_fields():
    import asyncio
    result = asyncio.run(_run_retriever("Credit risk assessment for SME loan application"))
    assert "credit_risk_score" in result
    assert "aml_flags" in result
    assert "fraud_signals" in result
    assert "composite_risk_score" in result
    assert "risk_level" in result
    assert "regulatory_refs" in result
    assert "recommendation" in result


def test_retriever_risk_level_is_valid():
    import asyncio
    result = asyncio.run(_run_retriever("Standard portfolio review"))
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_retriever_high_risk_on_npl():
    import asyncio
    result = asyncio.run(_run_retriever("Non-performing loan with no collateral and debt ratio exceeded"))
    assert result["credit_risk_score"] > 0
    assert result["composite_risk_score"] >= result["credit_risk_score"]


def test_retriever_aml_detection():
    import asyncio
    result = asyncio.run(_run_retriever("Suspicious layering and structuring via shell company"))
    assert len(result["aml_flags"]) >= 2
    assert any("AML" in ref or "AMLO" in result["recommendation"] for ref in result["regulatory_refs"])


def test_retriever_critical_triggers_sar():
    import asyncio
    result = asyncio.run(_run_retriever(
        "Non-performing loan layering structuring shell company fraud velocity anomaly geo-mismatch"
        " rapid succession unusual volume offshore third-party new payee"
    ))
    assert result["risk_level"] == "CRITICAL"
    assert "SAR" in result["recommendation"]


def test_retriever_regulatory_refs_populated():
    import asyncio
    result = asyncio.run(_run_retriever("Credit risk default NPL non-performing"))
    assert len(result["regulatory_refs"]) >= 1
    assert any("ธปท." in r or "Basel" in r for r in result["regulatory_refs"])


def test_retriever_transaction_data_velocity():
    import asyncio
    result = asyncio.run(_run_retriever(
        "Transaction review",
        tx={"velocity_anomaly": True, "days_overdue": 95},
    ))
    assert "velocity anomaly (transaction data)" in result["fraud_signals"]
    assert result["credit_risk_score"] >= 20


def test_retriever_composite_score_bounded():
    import asyncio
    result = asyncio.run(_run_retriever(
        "layering structuring smurfing offshore shell company third-party"
        " velocity anomaly geo-mismatch rapid succession unusual volume new payee"
    ))
    assert 0 <= result["composite_risk_score"] <= 100


# ── FintechSwarm integration tests ────────────────────────────────────────────


async def _collect_swarm(query: str, tx: dict | None = None) -> list[dict]:
    swarm = FintechSwarm()
    events = []
    async for event in swarm.analyze_risk(query, tx):
        events.append(event)
    return events


def test_swarm_emits_init_and_complete():
    import asyncio
    events = asyncio.run(_collect_swarm("Credit risk assessment for retail banking loan"))
    statuses = [e["status"] for e in events]
    assert "init" in statuses
    assert "risk_assessment_complete" in statuses


def test_swarm_final_report_has_bundle_hash():
    import asyncio
    events = asyncio.run(_collect_swarm("AML detection for corporate account"))
    final = next(e for e in events if e["status"] == "risk_assessment_complete")
    report = final["report"]
    assert "bundle_hash" in report
    assert len(report["bundle_hash"]) == 64  # SHA-256 hex


def test_swarm_bundle_hash_is_verifiable():
    import asyncio
    events = asyncio.run(_collect_swarm("Fraud signal: velocity anomaly detected"))
    final = next(e for e in events if e["status"] == "risk_assessment_complete")
    report = final["report"]
    claimed_hash = report.pop("bundle_hash")
    recomputed = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert claimed_hash == recomputed


def test_swarm_report_has_run_id_and_swarm_name():
    import asyncio
    events = asyncio.run(_collect_swarm("Standard credit review for SME"))
    final = next(e for e in events if e["status"] == "risk_assessment_complete")
    report = final["report"]
    assert report["swarm"] == "FintechSwarm"
    assert "run_id" in report
    assert "duration_seconds" in report


def test_swarm_phase1_complete_event_present():
    import asyncio
    events = asyncio.run(_collect_swarm("Portfolio stress test scenario"))
    statuses = [e["status"] for e in events]
    assert "phase_1_complete" in statuses


# ── API endpoint tests ────────────────────────────────────────────────────────

def test_fintech_analyze_endpoint(test_app):
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        with client.stream(
            "POST",
            "/swarms/fintech/analyze",
            json={"query": "Credit risk for retail banking customer with high leverage"},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            # Consume at least the first SSE line
            first_line = next(
                line for line in resp.iter_lines() if line.startswith("data:")
            )
            assert first_line


def test_fintech_template_endpoint(test_app):
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        resp = client.get("/swarms/fintech/template")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "fintech"
    assert "regulatory_tags" in data
