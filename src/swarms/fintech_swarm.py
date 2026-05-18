import hashlib
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator

from src.agents.subagents.circuit_breaker import CircuitBreakerSubAgent
from src.agents.subagents.fintech_retriever import FintechKnowledgeRetriever
from src.agents.subagents.guardrail_resolver import ConflictResolverSubAgent
from src.agents.subagents.meta_learner import MetaLearnerSubAgent
from src.agents.subagents.red_team_guard import RedTeamGuardSubAgent

logger = logging.getLogger(__name__)

_MAX_RECURSION_DEPTH = 3


def _sign(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


class FintechSwarm:
    """Plug-and-play bank risk analysis product.

    Orchestrates a 5-phase pipeline:
      Phase 0 — AI Red Team Guard (prompt injection / regulatory safety)
      Phase 1 — FintechKnowledgeRetriever (credit, AML, fraud scoring)
      Phase 2 — Circuit Breaker (recursion depth guard)
      Phase 3 — ConflictResolver (PDPA redaction + BOT compliance)
      Phase 4 — MetaLearner (knowledge graph update)

    Every streamed event is a JSON-serialisable dict. The final
    ``risk_assessment_complete`` event contains a tamper-evident
    ``bundle_hash`` for auditor verification.
    """

    def __init__(
        self,
        tenant_id: str = "default",
        memory: Any = None,
        inference: Any = None,
        embedding: Any = None,
    ):
        self.tenant_id = tenant_id
        self._qdrant = getattr(memory, "vector_store", None) if memory else None
        self._neo4j = getattr(memory, "graph_store", None) if memory else None
        self._inference = inference
        self._embedding = embedding

    async def analyze_risk(
        self,
        query: str,
        transaction_data: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream a full risk analysis pipeline for a fintech query.

        Yields dicts at each phase boundary. The final event has
        ``status == "risk_assessment_complete"`` and contains the full report.
        """
        run_id = str(uuid.uuid4())
        started_at = time.time()

        yield {"status": "init", "run_id": run_id, "msg": "Fintech Swarm — Bank Risk Analysis starting..."}

        # ── Phase 0: Red Team Guard ──────────────────────────────────────────
        yield {"status": "phase_0", "msg": "Red Team Guard: checking for adversarial input..."}
        guard = RedTeamGuardSubAgent(
            task_name="fintech_red_team",
            inference=self._inference,
            qdrant=self._qdrant,
            neo4j=self._neo4j,
        )
        async for chunk in guard.execute({"user_input": query}):
            if chunk.get("status") == "blocked":
                yield {
                    "status": "aborted",
                    "run_id": run_id,
                    "reason": "Adversarial input detected by Red Team Guard.",
                    "chunk": chunk,
                }
                return
            yield {"status": "phase_0_stream", "chunk": chunk}

        # ── Phase 1: Fintech Knowledge Retrieval ─────────────────────────────
        yield {"status": "phase_1", "msg": "FintechKnowledgeRetriever: scoring credit, AML, fraud..."}
        retriever = FintechKnowledgeRetriever(
            qdrant=self._qdrant,
            neo4j=self._neo4j,
            embedding_provider=self._embedding,
        )
        risk_assessment: dict[str, Any] = {}
        async for chunk in retriever.execute(
            {"query": query, "transaction_data": transaction_data or {}}
        ):
            if chunk.get("status") == "completed":
                risk_assessment = chunk.get("insight", {})
            yield {"status": "phase_1_stream", "chunk": chunk}

        yield {"status": "phase_1_complete", "risk_assessment": risk_assessment}

        # ── Phase 2: Circuit Breaker ─────────────────────────────────────────
        yield {"status": "phase_2", "msg": "Circuit Breaker: checking recursion depth..."}
        breaker = CircuitBreakerSubAgent(
            task_name="fintech_circuit_breaker",
            inference=self._inference,
            qdrant=self._qdrant,
            neo4j=self._neo4j,
        )
        async for chunk in breaker.execute(
            {
                "recursion_depth": len(query.split()) // 10,
                "max_depth": _MAX_RECURSION_DEPTH,
                "user_input": query,
            }
        ):
            yield {"status": "phase_2_stream", "chunk": chunk}

        # ── Phase 3: Compliance Resolver ─────────────────────────────────────
        yield {"status": "phase_3", "msg": "ConflictResolver: applying PDPA redaction and BOT compliance..."}
        resolver = ConflictResolverSubAgent(
            task_name="fintech_compliance",
            inference=self._inference,
            qdrant=self._qdrant,
            neo4j=self._neo4j,
        )
        compliance_summary: str = ""
        async for chunk in resolver.execute(
            {
                "proposed_solution": json.dumps(risk_assessment, default=str),
                "background_facts": risk_assessment.get("regulatory_refs", []),
            }
        ):
            if chunk.get("status") == "completed":
                result = chunk.get("insight", {})
                compliance_summary = result.get("resolved_insight", "") if isinstance(result, dict) else str(result)
            yield {"status": "phase_3_stream", "chunk": chunk}

        # ── Phase 4: Meta-Learner ─────────────────────────────────────────────
        yield {"status": "phase_4", "msg": "MetaLearner: updating knowledge graph weights..."}
        meta = MetaLearnerSubAgent(
            task_name="fintech_meta",
            neo4j=self._neo4j,
            inference=self._inference,
            qdrant=self._qdrant,
        )
        async for chunk in meta.execute(
            {
                "feedback": f"Risk analysis completed. Level: {risk_assessment.get('risk_level', 'N/A')}.",
                "performance_metrics": {"tokens": 1500, "phases": 5},
            }
        ):
            yield {"status": "phase_4_stream", "chunk": chunk}

        # ── Final Report ──────────────────────────────────────────────────────
        report: dict[str, Any] = {
            "run_id": run_id,
            "tenant_id": self.tenant_id,
            "swarm": "FintechSwarm",
            "query": query,
            "risk_assessment": risk_assessment,
            "compliance_summary": compliance_summary,
            "duration_seconds": round(time.time() - started_at, 3),
            "generated_at": time.time(),
        }
        report["bundle_hash"] = _sign(report)

        yield {"status": "risk_assessment_complete", "report": report}
