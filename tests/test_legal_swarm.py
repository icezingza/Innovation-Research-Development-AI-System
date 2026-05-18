"""Tests for LegalGraphExplorer and LegalSwarm."""

import hashlib
import json

from src.agents.subagents.legal_graph_explorer import LegalGraphExplorer
from src.swarms.legal_swarm import LegalSwarm


# ── LegalGraphExplorer unit tests ─────────────────────────────────────────────

_CONTRACT_WITH_PDPA = """
This Data Processing Agreement governs the collection and processing of personal data
by the Processor on behalf of the Controller. The Processor shall obtain explicit consent
from all data subjects prior to any data retention beyond the agreed period.
Cross-border transfer of personal data to servers outside Thailand requires a lawful basis
per PDPA guidelines. Biometric data shall not be processed without explicit written consent.
The indemnification clause requires the Processor to compensate the Controller for any breach of data processing obligations.
Limitation of liability shall apply unless gross negligence is proven by a court of competent jurisdiction.
Force majeure events include acts of god, war, and government-imposed restrictions.
"""

_CLEAN_CONTRACT = """
This Service Agreement governs the provision of consulting services between the parties.
Payment terms are net-30 days from invoice date. Either party may terminate this agreement
with 30 days written notice. All work product is the property of the Client upon full payment.
"""


async def _run_explorer(text: str, check_pdpa: bool = True) -> dict:
    explorer = LegalGraphExplorer()
    result = None
    async for chunk in explorer.execute(
        {"query": text[:100], "contract_text": text, "check_pdpa": check_pdpa}
    ):
        if chunk.get("status") == "completed":
            result = chunk["insight"]
    return result or {}


def test_explorer_returns_required_fields():
    import asyncio
    result = asyncio.run(_run_explorer(_CONTRACT_WITH_PDPA))
    assert "clauses_analyzed" in result
    assert "risk_clauses" in result
    assert "pdpa_findings" in result
    assert "pdpa_status" in result
    assert "contract_risk_level" in result
    assert "recommendations" in result
    assert "disclaimer" in result


def test_explorer_detects_pdpa_triggers():
    import asyncio
    result = asyncio.run(_run_explorer(_CONTRACT_WITH_PDPA))
    assert len(result["pdpa_findings"]) >= 3  # consent, personal data, cross-border transfer, retention


def test_explorer_pdpa_status_non_compliant_on_cross_border():
    import asyncio
    result = asyncio.run(_run_explorer(_CONTRACT_WITH_PDPA))
    # cross-border transfer is a CRITICAL trigger
    assert "NON_COMPLIANT" in result["pdpa_status"] or "REQUIRES_REVIEW" in result["pdpa_status"]


def test_explorer_clean_contract_compliant():
    import asyncio
    result = asyncio.run(_run_explorer(_CLEAN_CONTRACT))
    assert result["pdpa_status"] == "COMPLIANT"


def test_explorer_detects_indemnification_clause():
    import asyncio
    result = asyncio.run(_run_explorer(_CONTRACT_WITH_PDPA))
    clause_keywords = [c["clause_keyword"] for c in result["risk_clauses"]]
    assert "indemnification" in clause_keywords


def test_explorer_risk_clauses_have_law_references():
    import asyncio
    result = asyncio.run(_run_explorer(_CONTRACT_WITH_PDPA))
    for clause in result["risk_clauses"]:
        assert "law_reference" in clause
        assert clause["law_reference"]


def test_explorer_risk_level_valid():
    import asyncio
    result = asyncio.run(_run_explorer(_CONTRACT_WITH_PDPA))
    assert result["contract_risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_explorer_recommendations_non_empty():
    import asyncio
    result = asyncio.run(_run_explorer(_CONTRACT_WITH_PDPA))
    assert len(result["recommendations"]) >= 1


def test_explorer_pdpa_skip_when_disabled():
    import asyncio
    result = asyncio.run(_run_explorer(_CONTRACT_WITH_PDPA, check_pdpa=False))
    assert result["pdpa_findings"] == []
    assert result["pdpa_status"] == "COMPLIANT"


# ── LegalSwarm integration tests ──────────────────────────────────────────────


async def _collect_audit(text: str) -> list[dict]:
    swarm = LegalSwarm()
    events = []
    async for event in swarm.audit_contract(text):
        events.append(event)
    return events


async def _collect_pdpa(data_flows: list[str]) -> list[dict]:
    swarm = LegalSwarm()
    events = []
    async for event in swarm.check_pdpa(data_flows):
        events.append(event)
    return events


def test_audit_swarm_emits_init_and_complete():
    import asyncio
    events = asyncio.run(_collect_audit(_CONTRACT_WITH_PDPA))
    statuses = [e["status"] for e in events]
    assert "init" in statuses
    assert "contract_audit_complete" in statuses


def test_audit_swarm_final_report_has_bundle_hash():
    import asyncio
    events = asyncio.run(_collect_audit(_CLEAN_CONTRACT))
    final = next(e for e in events if e["status"] == "contract_audit_complete")
    assert "bundle_hash" in final["report"]
    assert len(final["report"]["bundle_hash"]) == 64


def test_audit_bundle_hash_is_verifiable():
    import asyncio
    events = asyncio.run(_collect_audit(_CONTRACT_WITH_PDPA))
    final = next(e for e in events if e["status"] == "contract_audit_complete")
    report = final["report"]
    claimed = report.pop("bundle_hash")
    recomputed = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert claimed == recomputed


def test_audit_report_mode_is_contract_audit():
    import asyncio
    events = asyncio.run(_collect_audit(_CLEAN_CONTRACT))
    final = next(e for e in events if e["status"] == "contract_audit_complete")
    assert final["report"]["mode"] == "contract_audit"
    assert final["report"]["swarm"] == "LegalSwarm"


def test_pdpa_check_emits_complete():
    import asyncio
    flows = [
        "Collect customer name and national ID for KYC verification",
        "Transfer health records to analytics platform in Singapore",
        "Biometric fingerprint scan for office access control",
    ]
    events = asyncio.run(_collect_pdpa(flows))
    statuses = [e["status"] for e in events]
    assert "pdpa_check_complete" in statuses


def test_pdpa_check_report_has_correct_mode():
    import asyncio
    events = asyncio.run(_collect_pdpa(["Collect email and name for newsletter"]))
    final = next(e for e in events if e["status"] == "pdpa_check_complete")
    report = final["report"]
    assert report["mode"] == "pdpa_check"
    assert report["data_flows_scanned"] == 1


def test_pdpa_check_bundle_hash_verifiable():
    import asyncio
    events = asyncio.run(_collect_pdpa(["Process biometric data without consent"]))
    final = next(e for e in events if e["status"] == "pdpa_check_complete")
    report = final["report"]
    claimed = report.pop("bundle_hash")
    recomputed = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert claimed == recomputed


# ── API endpoint tests ────────────────────────────────────────────────────────

def test_legal_audit_endpoint(test_app):
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        with client.stream(
            "POST",
            "/swarms/legal/audit",
            json={"contract_text": _CONTRACT_WITH_PDPA},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            first_line = next(
                line for line in resp.iter_lines() if line.startswith("data:")
            )
            assert first_line


def test_legal_pdpa_check_endpoint(test_app):
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        with client.stream(
            "POST",
            "/swarms/legal/pdpa-check",
            json={"data_flows": ["Transfer personal data to overseas servers without consent"]},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


def test_legal_template_endpoint(test_app):
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        resp = client.get("/swarms/legal/template")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "legal"
