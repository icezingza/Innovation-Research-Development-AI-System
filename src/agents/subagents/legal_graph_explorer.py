import logging
import re
from typing import Any

from src.agents.subagents.base import AntigravitySubAgent
from src.memory.neo4j_connector import Neo4jKnowledgeConnector

logger = logging.getLogger(__name__)

# Clause risk indicators and their Thai Civil Code references
_CLAUSE_RISKS: list[tuple[str, str, str]] = [
    ("indemnification", "HIGH", "ป.พ.พ. มาตรา 420 (Tort Liability)"),
    ("limitation of liability", "MEDIUM", "ป.พ.พ. มาตรา 373 (Condition of Validity)"),
    ("liquidated damages", "MEDIUM", "ป.พ.พ. มาตรา 383 (Penalty Clause)"),
    ("termination for convenience", "HIGH", "ป.พ.พ. มาตรา 386 (Notice of Termination)"),
    ("governing law", "LOW", "พ.ร.บ. ว่าด้วยการขัดกันแห่งกฎหมาย 2481"),
    ("force majeure", "LOW", "ป.พ.พ. มาตรา 8 (Impossible Performance)"),
    ("intellectual property", "HIGH", "พ.ร.บ. ลิขสิทธิ์ 2537"),
    ("non-compete", "HIGH", "ป.พ.พ. มาตรา 150 (Unlawful Object)"),
    ("data processing", "CRITICAL", "พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล 2562 (PDPA) มาตรา 24"),
    ("personal data", "CRITICAL", "PDPA มาตรา 6 — คำนิยามข้อมูลส่วนบุคคล"),
    ("consent", "HIGH", "PDPA มาตรา 19 — การขอความยินยอม"),
    ("data retention", "HIGH", "PDPA มาตรา 26 — การเก็บรักษาข้อมูล"),
    ("cross-border transfer", "CRITICAL", "PDPA มาตรา 28 — การส่งข้อมูลไปต่างประเทศ"),
]

_PDPA_TRIGGERS = [
    "personal data", "data subject", "controller", "processor", "consent",
    "sensitive data", "biometric", "health data", "retention period",
    "data breach", "transfer", "third party", "privacy notice",
]


class LegalGraphExplorer(AntigravitySubAgent):
    """Domain-specific explorer for Thai contract analysis and PDPA compliance mapping.

    Extracts risk clauses, maps each to Thai Civil Code / PDPA provisions,
    and produces a structured audit report with PDPA compliance status.
    """

    def __init__(
        self,
        task_name: str = "LegalGraphExplorer",
        max_tokens: int = 3000,
        neo4j: Neo4jKnowledgeConnector | None = None,
    ):
        super().__init__(task_name=task_name, max_tokens=max_tokens, max_depth=5)
        self.neo4j = neo4j

    async def _process_task(self) -> dict[str, Any]:
        query: str = self.ephemeral_memory.get("query", "")
        contract_text: str = self.ephemeral_memory.get("contract_text", query)
        check_pdpa: bool = self.ephemeral_memory.get("check_pdpa", True)
        text_lower = contract_text.lower()

        # --- Clause Risk Extraction ---
        risk_clauses = self._extract_risk_clauses(text_lower)
        self.current_tokens += 300

        # --- PDPA Compliance Mapping ---
        pdpa_findings: list[dict[str, str]] = []
        pdpa_status = "COMPLIANT"
        if check_pdpa:
            pdpa_findings = self._check_pdpa(text_lower)
            pdpa_status = self._pdpa_verdict(pdpa_findings)
        self.current_tokens += 200

        # --- Overall Contract Risk Score ---
        risk_score = self._contract_risk_score(risk_clauses)
        contract_risk_level = self._risk_level(risk_score)

        # --- Knowledge Graph Enrichment ---
        graph_precedents = await self._query_legal_graph(query)
        self.current_tokens += 150

        return {
            "domain": "legal",
            "query": query,
            "clauses_analyzed": len(risk_clauses),
            "risk_clauses": risk_clauses,
            "pdpa_findings": pdpa_findings,
            "pdpa_status": pdpa_status,
            "contract_risk_score": risk_score,
            "contract_risk_level": contract_risk_level,
            "graph_precedents": graph_precedents,
            "jurisdiction": "Thailand (Thai Civil and Commercial Code + PDPA 2562)",
            "disclaimer": (
                "This is an automated research summary. Review by a licensed Thai attorney "
                "is required before any legal reliance."
            ),
            "recommendations": self._recommendations(risk_clauses, pdpa_findings, pdpa_status),
        }

    def _extract_risk_clauses(self, text: str) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        for keyword, risk, law_ref in _CLAUSE_RISKS:
            if keyword in text:
                # Extract surrounding sentence for context
                idx = text.find(keyword)
                start = max(0, idx - 100)
                end = min(len(text), idx + 150)
                snippet = text[start:end].strip()
                snippet = re.sub(r"\s+", " ", snippet)
                findings.append({
                    "clause_keyword": keyword,
                    "risk": risk,
                    "law_reference": law_ref,
                    "excerpt": f"...{snippet}...",
                })
        return findings

    def _check_pdpa(self, text: str) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        for trigger in _PDPA_TRIGGERS:
            if trigger in text:
                law_ref = next(
                    (ref for kw, _, ref in _CLAUSE_RISKS if kw == trigger),
                    "PDPA 2562 — General Obligation",
                )
                findings.append({"trigger": trigger, "pdpa_reference": law_ref})
        return findings

    def _pdpa_verdict(self, findings: list[dict]) -> str:
        critical_triggers = {"cross-border transfer", "sensitive data", "biometric", "health data"}
        triggered = {f["trigger"] for f in findings}
        if critical_triggers & triggered:
            return "NON_COMPLIANT — Critical PDPA obligations triggered"
        if findings:
            return "REQUIRES_REVIEW — PDPA obligations present, manual audit needed"
        return "COMPLIANT"

    def _contract_risk_score(self, clauses: list[dict]) -> int:
        weights = {"CRITICAL": 30, "HIGH": 15, "MEDIUM": 8, "LOW": 3}
        return min(sum(weights.get(c["risk"], 0) for c in clauses), 100)

    def _risk_level(self, score: int) -> str:
        if score >= 80:
            return "CRITICAL"
        if score >= 60:
            return "HIGH"
        if score >= 35:
            return "MEDIUM"
        return "LOW"

    def _recommendations(
        self,
        clauses: list[dict],
        pdpa_findings: list[dict],
        pdpa_status: str,
    ) -> list[str]:
        recs: list[str] = []
        critical_clauses = [c for c in clauses if c["risk"] == "CRITICAL"]
        if critical_clauses:
            recs.append(
                f"URGENT: {len(critical_clauses)} critical clause(s) require immediate legal review "
                f"before execution."
            )
        if "NON_COMPLIANT" in pdpa_status:
            recs.append(
                "PDPA: Appoint a Data Protection Officer (DPO) and prepare a Record of Processing "
                "Activities (ROPA) per PDPA มาตรา 40."
            )
        elif "REQUIRES_REVIEW" in pdpa_status:
            recs.append(
                "PDPA: Prepare a Privacy Impact Assessment (PIA) and ensure lawful basis under PDPA มาตรา 24."
            )
        high_clauses = [c for c in clauses if c["risk"] == "HIGH"]
        if high_clauses:
            recs.append(
                f"{len(high_clauses)} high-risk clause(s) detected. Negotiate caps on liability "
                f"and ensure indemnification scope is limited."
            )
        if not recs:
            recs.append("Contract appears low-risk. Routine review recommended before signing.")
        return recs

    async def _query_legal_graph(self, query: str) -> str:
        if not self.neo4j:
            return "Knowledge graph unavailable (heuristic mode)."
        try:
            cypher = (
                "MATCH (n:Regulation) WHERE n.jurisdiction = 'Thailand' "
                "RETURN n.name AS name, n.reference AS reference LIMIT 3"
            )
            records = await self.neo4j.run_query(cypher, {"query": query})
            if records:
                return "; ".join(
                    f"{r['name']} ({r['reference']})" for r in records
                )
        except Exception as exc:
            logger.warning("Neo4j legal query failed: %s", exc)
        return "No precedent matches found."
