# IRD-AI OS v0.9.0 Strategic Improvement Design

**Author:** นะโม (AI Project Leader & Core Systems Architect)
**Date:** 2026-05-18
**Source:** strategic_improvement_plan.pdf — IRD-AI Sovereign Cognitive OS

---

## Executive Summary

Upgrade IRD-AI OS from v0.9.0 (functional prototype) to enterprise-grade
Autonomous Scientific Intelligence (ASI) platform targeting regulated-sector
institutional investors in Southeast Asia.

Four sprint areas ranked by PDF priority:

| Sprint | Section | Urgency (PDF) |
|--------|---------|---------------|
| S1 | Commercialization & Moats (Section 4) | Very High |
| S2 | Infrastructure & Observability (Section 1) | High |
| S3 | Cognitive Core & Self-Optimization (Section 2) | High |
| S4 | Hardened Air-Gapped Security (Section 3) | Medium |

---

## Sprint S1 — Commercialization & Moats

### Goal
Deliver investor-demo-ready Industry Swarm Templates and a Glass-Box Audit SDK
that differentiate IRD-AI from Black-Box AI competitors.

### What Already Exists
- `src/swarms/templates/fintech.yaml` / `health.yaml` / `legal.yaml` — scaffolded but thin
- `GET /research/tasks/{task_id}/trace` — JSON audit trail (no export format)
- `src/swarms/routes.py` — `/swarms`, `/swarms/tenants/{id}/activate`

### What Will Be Built
1. **Enrich YAML templates** — add 5+ KG seed nodes, regulatory_tags,
   industry-specific system_prompt per template
2. **GET /swarms/{id}** — new endpoint returning full template detail + KG seed preview
3. **Auditable Glass-Box SDK** (`src/audit/`)
   - `audit_sdk.py` — `AuditTrailExporter` class: formats trace events as JSON or HTML
   - `GET /research/tasks/{task_id}/trace?format=html` — downloadable audit report

### Interfaces
```python
class AuditTrailExporter:
    def export_json(self, task_id: str, events: list[dict]) -> dict
    def export_html(self, task_id: str, events: list[dict]) -> str
```

---

## Sprint S2 — Infrastructure & Observability

### Goal
Wire OpenTelemetry spans to Jaeger (Docker Compose) and add predictive FinOps
token/compute forecasting per tenant.

### What Already Exists
- `src/telemetry/tracing.py` — `configure_tracing()` with `ConsoleSpanExporter` only
- `docker-compose.yml` — postgres, redis, qdrant, neo4j, prometheus, api
- `GET /tenants/{id}/finops` — basic usage summary (no prediction)

### What Will Be Built
1. **OTLPSpanExporter in tracing.py** — env-gated (`OTEL_EXPORTER_OTLP_ENDPOINT`)
2. **Jaeger service in docker-compose.yml** — `jaegertracing/all-in-one:1.55`
3. **FinOps Predictor** (`src/billing/finops_predictor.py`)
   - Linear regression over last N usage snapshots → forecast next period
4. **GET /tenants/{id}/finops/forecast** — returns predicted tokens + compute cost

### Interfaces
```python
class FinOpsPredictor:
    def forecast(self, history: list[int], periods_ahead: int = 1) -> ForecastResult
```

---

## Sprint S3 — Cognitive Core & Self-Optimization

### Goal
Prevent runaway Multi-Agent debate loops via Circuit Breaker → Bayesian synthesis,
and create a Speculative Knowledge Graph pipeline for continual meta-learning.

### What Already Exists
- `src/orchestration/debate_runtime.py` — `DebateRuntime`, `max_rounds=3`
- `src/reasoning/recursive_loop.py` — `RecursiveReasoningLoop`, `max_depth=5`
- `src/reasoning/math_engine/golden_bayesian.py` — `GoldenBayesian.batch_update()`
- `src/memory/knowledge_graph.py` — `KnowledgeGraph` with Hypothesis/Statement nodes

### What Will Be Built
1. **Circuit Breaker in DebateRuntime**
   - Detect repeated argument hash (stale debate) within rounds
   - On trigger: call `GoldenBayesian.batch_update()` over all round scores → forced synthesis
2. **MetaLearning Pipeline** (`src/reasoning/meta_learning.py`)
   - `MetaLearningPipeline.ingest(feedback)` — stores critique-agent feedback
     as `(:SpeculativeKnowledge)` nodes in Neo4j
3. **Cross-Domain Ontology** (`src/memory/knowledge_graph.py` extension)
   - `store_domain_concept(domain, concept, properties)` → `(:Domain)-[:CONTAINS]->(:Concept)`

### Circuit Breaker Logic
```
rounds complete without convergence AND
  any two consecutive argument hashes are equal
→ extract scores from all rounds
→ GoldenBayesian.batch_update(prior=0.5, evidence_scores, contradiction_flags)
→ return DebateResult(converged=False, convergence_reason="circuit_breaker")
```

---

## Sprint S4 — Hardened Air-Gapped Security

### Goal
Add Customer-Managed Encryption Keys (CMK) per tenant and an active
AI Red Teaming middleware that continuously stress-tests the Policy Enforcer.

### What Already Exists
- `src/security/regulatory_guard.py` — `RegulatoryGuard` (pattern-match rules)
- `src/governance/audit_log.py` — `GovernanceAuditLog`

### What Will Be Built
1. **CMK Module** (`src/security/cmk.py`)
   - Per-tenant Fernet key generation + Redis storage
   - `encrypt(tenant_id, plaintext)` / `decrypt(tenant_id, ciphertext)` API
2. **Red Teaming Middleware** (`src/security/red_team_middleware.py`)
   - `RedTeamMiddleware` — async background task running adversarial prompts
     against `RegulatoryGuard` on startup and periodically
   - Logs blocked/passed results to `GovernanceAuditLog`

### Security Constraints
- CMK keys stored in Redis with TTL=0 (permanent) under key `cmk:{tenant_id}`
- Red teaming runs in background — never blocks request path
- Adversarial prompt corpus is static YAML (`src/security/red_team_corpus.yaml`)

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  S1 — Commercialization                                          │
│  ┌─────────────────────┐   ┌────────────────────────────────┐   │
│  │ Swarm Templates      │   │ Audit SDK                      │   │
│  │ fintech/health/legal │──▶│ AuditTrailExporter (JSON/HTML) │   │
│  │ enriched YAML        │   │ GET /tasks/{id}/trace?format=  │   │
│  └─────────────────────┘   └────────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│  S2 — Observability                                              │
│  tracing.py ──OTLP──▶ Jaeger :16686                             │
│  finops_predictor.py ──▶ GET /tenants/{id}/finops/forecast       │
├──────────────────────────────────────────────────────────────────┤
│  S3 — Cognitive Core                                             │
│  DebateRuntime ──hash check──▶ Circuit Breaker                   │
│  Circuit Breaker ──▶ GoldenBayesian.batch_update()              │
│  MetaLearningPipeline ──▶ Neo4j :SpeculativeKnowledge           │
├──────────────────────────────────────────────────────────────────┤
│  S4 — Security                                                   │
│  CMK (Fernet) ──▶ Redis cmk:{tenant_id}                         │
│  RedTeamMiddleware ──▶ RegulatoryGuard ──▶ GovernanceAuditLog   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy
- Every new class covered by pytest unit tests before implementation
- Integration tests (async) for all new API endpoints
- Security tests for CMK encrypt/decrypt round-trip
- No mocking of `RegulatoryGuard` — use real corpus in red team tests
