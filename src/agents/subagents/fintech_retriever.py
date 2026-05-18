import logging
from typing import Any

from src.agents.subagents.base import AntigravitySubAgent
from src.memory.qdrant_connector import QdrantMemoryConnector
from src.memory.neo4j_connector import Neo4jKnowledgeConnector

logger = logging.getLogger(__name__)

# Risk scoring thresholds (0-100 scale)
_CRITICAL_THRESHOLD = 80
_HIGH_THRESHOLD = 60
_MEDIUM_THRESHOLD = 35

_AML_KEYWORDS = [
    "layering", "structuring", "smurfing", "shell company", "offshore",
    "wire transfer", "cryptocurrency", "cash intensive", "trade-based",
]
_FRAUD_SIGNALS = [
    "unusual volume", "rapid succession", "dormant account", "third-party",
    "velocity anomaly", "geo-mismatch", "new payee", "round-amount",
]
_BOT_REFS = {
    "credit": "ธปท. ประกาศ รส. 4/2566 (Credit Risk Management)",
    "aml": "ธปท. ประกาศ สสช. 21/2565 (AML/CFT Guidelines)",
    "fraud": "ธปท. ประกาศ ฝศป. 3/2566 (Fraud Prevention Framework)",
    "capital": "Basel III — Capital Adequacy Ratio Requirement (BIS)",
    "sec": "กลต. พ.ร.บ.หลักทรัพย์และตลาดหลักทรัพย์ 2535",
}


class FintechKnowledgeRetriever(AntigravitySubAgent):
    """Domain-specific knowledge retriever for Thai fintech risk intelligence.

    Scores credit risk, detects AML patterns and fraud signals, and maps findings
    to Bank of Thailand (BOT) and SEC regulatory references.
    """

    def __init__(
        self,
        task_name: str = "FintechKnowledgeRetriever",
        max_tokens: int = 2500,
        qdrant: QdrantMemoryConnector | None = None,
        neo4j: Neo4jKnowledgeConnector | None = None,
        embedding_provider: Any = None,
    ):
        super().__init__(task_name=task_name, max_tokens=max_tokens, max_depth=3)
        self.qdrant = qdrant
        self.neo4j = neo4j
        self.embedding_provider = embedding_provider

    async def _process_task(self) -> dict[str, Any]:
        query: str = self.ephemeral_memory.get("query", "")
        transaction_data: dict = self.ephemeral_memory.get("transaction_data", {})
        query_lower = query.lower()

        # --- Credit Risk Score ---
        credit_score = self._score_credit_risk(query_lower, transaction_data)
        self.current_tokens += 200

        # --- AML Detection ---
        aml_flags = [kw for kw in _AML_KEYWORDS if kw in query_lower]
        self.current_tokens += 150

        # --- Fraud Signal Detection ---
        fraud_signals = [sig for sig in _FRAUD_SIGNALS if sig in query_lower]
        if transaction_data.get("velocity_anomaly"):
            fraud_signals.append("velocity anomaly (transaction data)")
        self.current_tokens += 150

        # --- Composite Risk Score ---
        aml_weight = min(len(aml_flags) * 15, 40)
        fraud_weight = min(len(fraud_signals) * 12, 35)
        composite_score = min(credit_score + aml_weight + fraud_weight, 100)

        risk_level = self._risk_level(composite_score)

        # --- Regulatory Reference Mapping ---
        regulatory_refs: list[str] = []
        if credit_score > 30:
            regulatory_refs.append(_BOT_REFS["credit"])
        if aml_flags:
            regulatory_refs.append(_BOT_REFS["aml"])
        if fraud_signals:
            regulatory_refs.append(_BOT_REFS["fraud"])
        if not regulatory_refs:
            regulatory_refs.append(_BOT_REFS["capital"])

        # --- Neo4j Graph Enrichment (best-effort) ---
        graph_context = await self._query_knowledge_graph(query)
        self.current_tokens += 100

        return {
            "domain": "fintech",
            "query": query,
            "credit_risk_score": credit_score,
            "aml_flags": aml_flags,
            "fraud_signals": fraud_signals,
            "composite_risk_score": composite_score,
            "risk_level": risk_level,
            "regulatory_refs": regulatory_refs,
            "graph_context": graph_context,
            "recommendation": self._recommendation(risk_level, aml_flags, fraud_signals),
        }

    def _score_credit_risk(self, query_lower: str, tx: dict) -> int:
        score = 0
        if any(w in query_lower for w in ["default", "non-performing", "npl", "overdue"]):
            score += 30
        if any(w in query_lower for w in ["high leverage", "debt ratio", "negative equity"]):
            score += 25
        if any(w in query_lower for w in ["no collateral", "unsecured", "micro loan"]):
            score += 15
        if tx.get("days_overdue", 0) > 90:
            score += 20
        return min(score, 60)

    def _risk_level(self, score: int) -> str:
        if score >= _CRITICAL_THRESHOLD:
            return "CRITICAL"
        if score >= _HIGH_THRESHOLD:
            return "HIGH"
        if score >= _MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "LOW"

    def _recommendation(self, risk_level: str, aml_flags: list, fraud_signals: list) -> str:
        if risk_level == "CRITICAL":
            return "Escalate to SAR filing (Suspicious Activity Report) and freeze account pending investigation."
        if aml_flags:
            return "Submit STR to Anti-Money Laundering Office (AMLO) and conduct Enhanced Due Diligence."
        if fraud_signals:
            return "Trigger real-time fraud alert and request customer verification before processing."
        if risk_level == "HIGH":
            return "Apply enhanced credit monitoring and require additional collateral documentation."
        if risk_level == "MEDIUM":
            return "Standard credit review cycle; flag for next quarterly risk committee."
        return "No immediate action required; maintain routine monitoring."

    async def _query_knowledge_graph(self, query: str) -> str:
        if not self.neo4j:
            return "Knowledge graph unavailable (heuristic mode)."
        try:
            cypher = (
                "MATCH (n:Regulation)-[r]->(m:RiskCategory) "
                "WHERE n.jurisdiction = 'Thailand' "
                "RETURN n.name AS regulation, m.name AS risk_category LIMIT 3"
            )
            records = await self.neo4j.run_query(cypher, {"query": query})
            if records:
                return "; ".join(
                    f"{r['regulation']} → {r['risk_category']}" for r in records
                )
        except Exception as exc:
            logger.warning("Neo4j query failed: %s", exc)
        return "No graph matches found."
