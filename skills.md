# System Skills & Capabilities Reference
# Innovation Research & Development AI System (IRDS)

**Version:** 1.0  
**Date:** 2026-05-17

This document describes the complete set of cognitive and operational capabilities delivered by IRDS as of Phase 9.

---

## 1. Core Cognitive Skills

### 1.1 Hypothesis Generation

**Component:** `HypothesisAgent`  
**Endpoint:** Invoked via `/cognition/coordinate` or `/research/workflows`

The system generates scientific hypotheses for any research question. Each hypothesis is:
- Grounded in prior knowledge recalled from semantic memory (if available)
- Confidence-calibrated (0.0–1.0 score)
- Associated with a generation counter (0 = initial, 1+ = evolved)
- Sourced and traceable to the originating agent and session

**Modes:**
- **LLM-augmented:** Uses InferenceRouter to generate rich, domain-specific hypotheses
- **Heuristic:** Template-based fallback without external API — always available

**Example:**
```
Goal: "What mechanisms enable high-temperature superconductivity?"
→ Hypothesis: "Magnetic fluctuations mediate Cooper pair formation at elevated temperatures,
   enabled by cuprate lattice geometry and hole-doping concentration above a critical threshold."
   confidence: 0.76, generation: 0
```

---

### 1.2 Hypothesis Critique

**Component:** `CritiqueAgent`  
**Invoked as part of coordination pipeline**

The system stress-tests generated hypotheses to identify weaknesses before synthesis:
- Identifies missing evidence
- Detects logical contradictions with prior findings
- Suggests targeted confidence adjustments (-0.1 to +0.05)
- Produces critique summaries for synthesis phase

---

### 1.3 Hypothesis Evolution

**Component:** `HypothesisEvolutionEngine` (used by `ResearchAgent`)

Hypotheses improve across generations:
1. `ReflectionEngine` identifies gaps (missing evidence, weak conclusions)
2. `HypothesisEvolutionEngine` qualifies the statement with required conditions
3. Generation counter increments (0 → 1 → 2 → ...)
4. Confidence recalibrated after each evolution step

**Example evolution:**
```
Gen 0: "Phonons enable Cooper pairing."
Gen 1: "Phonon-mediated Cooper pairing requires lattice vibration frequencies
        above 40THz, observable only in materials with low electron-phonon coupling loss."
```

---

### 1.4 Multi-Hypothesis Synthesis

**Component:** `SynthesisAgent`

Given multiple competing hypotheses and their critiques, the system:
1. Scores each hypothesis via ReflectionEngine
2. Ranks by quality score
3. Selects the primary hypothesis
4. Synthesizes a coherent research conclusion using the LLM (fast or deep tier)
5. Reports synthesis method and quality metrics

---

### 1.5 Recursive Reasoning

**Component:** `RecursiveReasoningLoop`

The system iteratively refines a hypothesis until convergence:
- Applies GoldenBayesian confidence updates each iteration
- Checks convergence conditions: quality_threshold | no_improvement | max_depth
- Configurable depth (default auto-tuned by AdaptiveConfigManager)
- Records every iteration in ReasoningTrace for auditability

**Convergence signals:**
```
quality_score >= 0.85                    → threshold reached
|score[n] - score[n-1]| < 0.02 (×2)    → no improvement
depth >= max_depth                       → depth limit
quality_declining AND contradictions     → early stop
```

---

### 1.6 Multi-Round Debate

**Component:** `DebateRuntime`

The system runs structured adversarial debate between competing hypotheses:
- Multiple debate rounds (default 3)
- Hypothesis advocates and critiques alternate
- Produces a `DebateResult` with final standing and round-by-round analysis

---

### 1.7 Contradiction Detection

**Component:** `ContradictionAnalyzer`

Detects logical inconsistencies across hypothesis sets:
- Compares statements pairwise for logical conflict
- Produces contradiction pairs with explanation
- Used by ResearchAgent to flag conflicting findings in memory
- Results stored as CONTRADICTS edges in Neo4j knowledge graph

---

### 1.8 Quality Reflection

**Component:** `ReflectionEngine`

Evaluates the quality of any hypothesis statement:
- Detects gaps: missing evidence, absent conclusion, overconfidence without justification
- Detects strengths: evidence-backed, explicit confidence, references prior findings
- Returns quality_score in [0.0, 1.0] and actionable suggestions

**Quality formula:**
```
quality_score = strengths / (gaps + strengths)
```

---

## 2. Memory & Knowledge Skills

### 2.1 Cross-Session Knowledge Accumulation

**Component:** `ResearchMemory`

Knowledge does not evaporate between sessions. Every high-confidence finding is stored to:
- In-memory ring buffer (immediate access)
- PostgreSQL (permanent, queryable)
- Qdrant (semantic, discoverable)

On new research: prior findings are recalled and injected into agent perception before hypothesis generation begins.

---

### 2.2 Semantic Memory Recall

**Component:** `ContextEngine` + Qdrant

Given any research topic, the system retrieves semantically similar past findings:
- Generates embedding (384-dim) from the topic query
- Searches Qdrant collection `research_hypotheses` by cosine similarity
- Returns top-N entries with `continuity_score` (average similarity)
- Fallback: keyword overlap scoring from ring buffer if Qdrant unavailable

---

### 2.3 Hypothesis Lineage Tracking

**Component:** `KnowledgeGraph` (Neo4j)

The system maintains a full graph of hypothesis provenance:
- Every hypothesis stored as a node with generation, confidence, session context
- EVOLVED_FROM edges link each generation to its predecessor
- CONTRADICTS edges link conflicting hypotheses
- Lineage queryable via `/intelligence/report`

---

### 2.4 Autonomous Gap Detection

**Component:** `ResearchAgenda`

The system identifies what it doesn't know and prioritizes next research:
- Scans ResearchMemory for topics with:
  - Low average confidence (< 0.55)
  - Insufficient coverage (< 3 entries per topic)
- Computes priority score (1–10)
- Generates suggested follow-up questions per gap
- Accessible at `/intelligence/agenda`

---

## 3. Orchestration Skills

### 3.1 Parallel Multi-Agent Coordination

**Component:** `AgentCoordinator`

For a research goal, the system:
1. Decomposes into sub-questions
2. Runs HypothesisAgent for each sub-question in parallel (`asyncio.gather`)
3. Runs CritiqueAgent for each hypothesis in parallel
4. Synthesizes all into a final conclusion
5. Returns `CoordinatedResult` with full output and event count

**Parallelism:** All sub-question hypotheses generated concurrently. All critiques generated concurrently.

---

### 3.2 Full Autonomous Research Workflow

**Component:** `ResearchWorkflow`

End-to-end autonomous research with real-time progress:
1. Recall prior context from memory
2. Decompose goal into sub-questions
3. Run parallel CognitivePipeline per sub-question (full hypothesis lifecycle)
4. Optional: multi-round debate between top hypotheses
5. Optional: recursive convergence refinement
6. Synthesize final conclusion
7. Store primary hypothesis to knowledge graph
8. Publish all progress events to SSE stream

---

### 3.3 Real-Time Progress Streaming

**Component:** `StreamManager` + SSE endpoint

Clients can subscribe to workflow progress via Server-Sent Events:
```
GET /streams/workflows/{workflow_id}
→ planning_started → planning_done → sub_question_complete (×N)
  → debate_complete → recursive_complete → synthesis_done → complete
```

Each event includes timestamp, relevant metrics, and phase-specific data.

---

### 3.4 Cognitive Session Management

**Component:** `CognitiveSessionManager`

Sessions maintain research context across multiple API calls:
- Tracks goals, workflow IDs, and findings count
- Redis-backed with 24h TTL (LRU in-memory fallback)
- Supports multi-call research campaigns with coherent state
- Accessible via `/sessions` CRUD endpoints

---

## 4. Adaptive Skills

### 4.1 Automatic Quality Tracking

**Component:** `QualityTracker`

After each research cycle, the system:
- Analyzes recent ReasoningTrace entries
- Detects trend by comparing first vs. second half average quality scores
- Reports: `improving` | `stable` | `declining` with per-operation statistics

---

### 4.2 Self-Tuning Configuration

**Component:** `AdaptiveConfigManager`

Based on quality trend:
- **Improving:** increase complexity (max_depth +1, max_sub_questions +1)
- **Declining:** reduce complexity (max_depth -1, max_sub_questions -1)
- **Stable:** no change

Bounds: max_depth ∈ [2, 8], max_sub_questions ∈ [2, 8]

The system becomes progressively more ambitious in good conditions and more conservative when quality degrades.

---

### 4.3 Graceful Degradation

The system fully operates with zero external services:
- No Qdrant → keyword-based recall from ring buffer
- No PostgreSQL → in-memory ring buffer only
- No Redis → in-memory sessions, RuntimeEventBus for events
- No Neo4j → skip lineage graph, no error
- No LLM providers → heuristic hypothesis generation
- No embeddings API → local SentenceTransformer always available

---

## 5. Inference Skills

### 5.1 Multi-Provider LLM Routing

**Component:** `InferenceRouter`

Unified interface across all LLM providers:
- Selects provider by reasoning tier (fast or deep)
- Auto-upgrades tier on failure if configured
- Logs all routing decisions to ReasoningTrace
- Supports: OpenAI, Gemini, DeepSeek, Ollama (local), OpenRouter

---

### 5.2 Semantic Embedding Generation

**Component:** `EmbeddingProvider`

Converts text to dense vector representations:
- Local: `all-MiniLM-L6-v2` (384 dimensions) — always available, no API
- Remote: `text-embedding-3-small` (1536 dimensions) — if OpenAI configured
- Used for: Qdrant storage and ContextEngine recall

---

## 6. Governance & Safety Skills

### 6.1 Policy Enforcement

**Component:** `PolicyEnforcer`

Every agent message is evaluated before execution:
- Content size limits enforced (prevents token runaway)
- Sender identity validated
- Decision: ALLOW | WARN | DENY
- All decisions recorded to GovernanceAuditLog

---

### 6.2 Complete Audit Trail

**Component:** `GovernanceAuditLog`

Every PolicyEnforcer decision is permanently recorded:
- In-memory for fast access
- Redis for cross-process visibility
- Accessible via `/governance/audit` endpoint
- Append-only — never modified or deleted

---

### 6.3 Multi-Tenant Isolation

**Component:** JWT auth + TenantMiddleware + PostgreSQL RLS

Full enterprise-grade tenant isolation:
- JWT tokens carry tenant_id claim
- TenantMiddleware sets `app.tenant_id` on every DB connection
- PostgreSQL RLS policies enforce row-level filtering at the database
- One tenant's data is never visible to another tenant

---

## 7. Observability Skills

### 7.1 Prometheus Metrics

Available at `/metrics`:
```
irds_active_agents_total          ← current running agents
irds_runtime_events_total         ← labeled by event_type
irds_reasoning_latency_seconds    ← histogram per operation type
irds_hypothesis_quality           ← histogram of quality scores
irds_memory_recall_latency_seconds ← recall operation latency
```

### 7.2 Distributed Tracing

OpenTelemetry spans emitted for:
- Every agent cycle (`agent.{id}.cycle`)
- Every inference call (`inference.{provider}.complete`)
- Every orchestration flow (`orchestration.research_workflow`)
- Every memory operation (`memory.qdrant.search`, `memory.postgres.insert`)

### 7.3 Reasoning Trace

Complete operational audit via `ReasoningTrace`:
- Every inference call, reflection analysis, recursion iteration recorded
- 3-tier storage: in-memory → Redis → PostgreSQL
- Queryable via `/reasoning/traces`

---

## 8. API Skills Summary

| Capability | Method | Path |
|------------|--------|------|
| Multi-agent coordination | POST | `/cognition/coordinate` |
| Full research workflow | POST | `/research/workflows` |
| Get workflow result | GET | `/research/workflows/{id}` |
| Async research task | POST | `/research/tasks` |
| Real-time workflow progress | GET | `/streams/workflows/{id}` |
| Recall from memory | GET | `/intelligence/recall?topic=...` |
| Intelligence report | GET | `/intelligence/report` |
| Research agenda | GET | `/intelligence/agenda` |
| Execute agenda item | POST | `/agenda/run` |
| Reasoning traces | GET | `/reasoning/traces` |
| Governance audit log | GET | `/governance/audit` |
| Create session | POST | `/sessions` |
| Get session | GET | `/sessions/{id}` |
| Runtime status | GET | `/runtime/status` |
| Dashboard metrics | GET | `/dashboard/metrics` |
| Liveness probe | GET | `/health` |
| Prometheus metrics | GET | `/metrics` |

---

## 9. Capability Limitations (Current)

| Limitation | Status | Planned |
|------------|--------|---------|
| Horizontal agent worker scaling | Single-process only | Phase 10 |
| External evidence retrieval (arXiv, PubMed) | Not implemented | Phase 12 |
| Hypothesis tournament (bracket-style) | Not implemented | Phase 11 |
| Long-running multi-day research campaigns | Not implemented | Phase 12 |
| Temporal reasoning (time-aware hypotheses) | Not implemented | Phase 11 |
| Multi-language hypothesis generation | Not implemented | Backlog |
| Structured PDF research report export | Not implemented | Phase 12 |
| Persistent agent identity across sessions | Partial (session-level only) | Phase 12 |
