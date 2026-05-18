import hashlib
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator

from src.agents.subagents.guardrail_resolver import ConflictResolverSubAgent
from src.agents.subagents.legal_graph_explorer import LegalGraphExplorer
from src.agents.subagents.meta_learner import MetaLearnerSubAgent
from src.telemetry.instrumentation import CognitiveAttr, record_pdpa_outcome
from src.telemetry.tracing import tracer

logger = logging.getLogger(__name__)


def _sign(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


class LegalSwarm:
    """Plug-and-play contract audit and PDPA compliance product.

    Exposes two entry-points:
      • ``audit_contract(contract_text)`` — full contract risk analysis
      • ``check_pdpa(data_flows)`` — focused PDPA compliance scan

    Every streamed event is a JSON-serialisable dict. The final event carries
    a tamper-evident ``bundle_hash`` for auditor verification (PwC / Deloitte).
    """

    def __init__(
        self,
        tenant_id: str = "default",
        memory: Any = None,
        inference: Any = None,
    ):
        self.tenant_id = tenant_id
        self._neo4j = getattr(memory, "graph_store", None) if memory else None
        self._qdrant = getattr(memory, "vector_store", None) if memory else None
        self._inference = inference

    async def audit_contract(
        self,
        contract_text: str,
        query: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream a contract audit pipeline.

        Phases:
          1 — LegalGraphExplorer (clause extraction + PDPA mapping)
          2 — ConflictResolver (regulatory compliance pass)
          3 — MetaLearner (knowledge graph update)

        Final event: ``status == "contract_audit_complete"`` with signed report.
        """
        run_id = str(uuid.uuid4())
        started_at = time.time()
        effective_query = query or contract_text[:200]

        yield {
            "status": "init",
            "run_id": run_id,
            "msg": "Legal Swarm — Contract Audit & PDPA Compliance starting...",
        }

        # ── Phase 1: LegalGraphExplorer ───────────────────────────────────────
        yield {"status": "phase_1", "msg": "LegalGraphExplorer: extracting risk clauses and PDPA triggers..."}
        explorer = LegalGraphExplorer(neo4j=self._neo4j)
        audit_result: dict[str, Any] = {}
        with tracer.start_as_current_span("legal.phase_1.contract_analysis") as p1_span:
            p1_span.set_attribute(CognitiveAttr.DOMAIN, "legal")
            p1_span.set_attribute(CognitiveAttr.PHASE, "contract_analysis")
            p1_span.set_attribute(CognitiveAttr.RUN_ID, run_id)
            async for chunk in explorer.execute(
                {"query": effective_query, "contract_text": contract_text, "check_pdpa": True}
            ):
                if chunk.get("status") == "completed":
                    audit_result = chunk.get("insight", {})
                yield {"status": "phase_1_stream", "chunk": chunk}
            record_pdpa_outcome(p1_span, audit_result.get("pdpa_status", "UNKNOWN"))

        yield {"status": "phase_1_complete", "audit_result": audit_result}

        # ── Phase 2: Compliance Resolver ─────────────────────────────────────
        yield {"status": "phase_2", "msg": "ConflictResolver: applying PDPA redaction and legal compliance check..."}
        resolver = ConflictResolverSubAgent(
            task_name="legal_compliance",
            inference=self._inference,
            qdrant=self._qdrant,
            neo4j=self._neo4j,
        )
        compliance_note: str = ""
        async for chunk in resolver.execute(
            {
                "proposed_solution": json.dumps(audit_result, default=str),
                "background_facts": audit_result.get("recommendations", []),
            }
        ):
            if chunk.get("status") == "completed":
                result = chunk.get("insight", {})
                compliance_note = result.get("resolved_insight", "") if isinstance(result, dict) else str(result)
            yield {"status": "phase_2_stream", "chunk": chunk}

        # ── Phase 3: Meta-Learner ─────────────────────────────────────────────
        yield {"status": "phase_3", "msg": "MetaLearner: updating legal knowledge graph..."}
        meta = MetaLearnerSubAgent(
            task_name="legal_meta",
            neo4j=self._neo4j,
            inference=self._inference,
            qdrant=self._qdrant,
        )
        async for chunk in meta.execute(
            {
                "feedback": f"Contract audit completed. PDPA status: {audit_result.get('pdpa_status', 'N/A')}.",
                "performance_metrics": {"clauses_analyzed": audit_result.get("clauses_analyzed", 0)},
            }
        ):
            yield {"status": "phase_3_stream", "chunk": chunk}

        # ── Final Report ──────────────────────────────────────────────────────
        report: dict[str, Any] = {
            "run_id": run_id,
            "tenant_id": self.tenant_id,
            "swarm": "LegalSwarm",
            "mode": "contract_audit",
            "audit_result": audit_result,
            "compliance_note": compliance_note,
            "duration_seconds": round(time.time() - started_at, 3),
            "generated_at": time.time(),
        }
        report["bundle_hash"] = _sign(report)

        yield {"status": "contract_audit_complete", "report": report}

    async def check_pdpa(
        self,
        data_flows: list[str],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream a focused PDPA compliance check against a list of data flow descriptions."""
        run_id = str(uuid.uuid4())
        started_at = time.time()
        combined_text = " ".join(data_flows).lower()

        yield {"status": "init", "run_id": run_id, "msg": "Legal Swarm — PDPA Compliance Scan starting..."}

        yield {"status": "phase_1", "msg": "LegalGraphExplorer: scanning data flows for PDPA obligations..."}
        explorer = LegalGraphExplorer(neo4j=self._neo4j)
        pdpa_result: dict[str, Any] = {}
        async for chunk in explorer.execute(
            {"query": combined_text, "contract_text": combined_text, "check_pdpa": True}
        ):
            if chunk.get("status") == "completed":
                pdpa_result = chunk.get("insight", {})
            yield {"status": "phase_1_stream", "chunk": chunk}

        report: dict[str, Any] = {
            "run_id": run_id,
            "tenant_id": self.tenant_id,
            "swarm": "LegalSwarm",
            "mode": "pdpa_check",
            "data_flows_scanned": len(data_flows),
            "pdpa_findings": pdpa_result.get("pdpa_findings", []),
            "pdpa_status": pdpa_result.get("pdpa_status", "UNKNOWN"),
            "recommendations": pdpa_result.get("recommendations", []),
            "duration_seconds": round(time.time() - started_at, 3),
            "generated_at": time.time(),
        }
        report["bundle_hash"] = _sign(report)

        yield {"status": "pdpa_check_complete", "report": report}
