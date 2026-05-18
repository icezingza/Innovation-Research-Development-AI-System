# System Design Document
# Innovation Research & Development AI System (IRDS)

**Version:** 1.0  
**Date:** 2026-05-17  
**Status:** Production-Ready (Phases 1–9)

---

## 1. Design Philosophy

This system is built around four foundational principles:

1. **Cognition must be persistent** — knowledge does not evaporate between sessions
2. **Reasoning must be observable** — every inference step is traced, logged, and auditable
3. **Architecture must be composable** — services connect through explicit contracts, not hidden coupling
4. **The system must degrade gracefully** — heuristic mode when external services are unavailable

These principles drive every design decision in the system. When in doubt, prefer observable, explicit, and composable over fast, convenient, or magical.

---

## 2. High-Level Design

### 2.1 System Context

```
External Users / API Clients
         │
         ▼
┌─────────────────────────────────────┐
│           FastAPI Application        │
│   (REST + SSE, Auth, Rate Limiting)  │
└────────────────┬────────────────────┘
                 │
    ┌────────────┴─────────────┐
    │    Orchestration Layer    │
    │ (Workflows, Coordination) │
    └────────────┬─────────────┘
                 │
    ┌────────────┴────────────────────────────────────┐
    │              Agent Layer                        │
    │  (Hypothesis, Critique, Synthesis, Research,    │
    │   Memory) — event-driven, async, parallel       │
    └────────────┬────────────────────────────────────┘
                 │
    ┌────────────┴────────────────────────────────────┐
    │         Reasoning & Cognition Layer             │
    │  (Reflection, Evolution, Contradiction,         │
    │   Quality, Adaptive Config, Recursion)          │
    └────────────┬────────────────────────────────────┘
                 │
    ┌────────────┴────────────────────────────────────┐
    │              Infrastructure Layer               │
    │   (EventBus, Scheduler, WorkerPool, Sessions,   │
    │    Spawner, StreamManager)                      │
    └────────────┬────────────────────────────────────┘
                 │
    ┌────────────┴────────────────────────────────────┐
    │               Memory Layer (4-tier)             │
    │  In-Memory │ Redis │ PostgreSQL │ Qdrant │ Neo4j│
    └────────────┬────────────────────────────────────┘
                 │
    ┌────────────┴────────────────────────────────────┐
    │          Governance & Security                  │
    │  (PolicyEnforcer, AuditLog, RLS, APIKeyManager) │
    └────────────┬────────────────────────────────────┘
                 │
    ┌────────────┴────────────────────────────────────┐
    │          Inference Layer (Pluggable LLMs)       │
    │  OpenAI │ Gemini │ DeepSeek │ Ollama │ Heuristic│
    └─────────────────────────────────────────────────┘
```

---

## 3. Core Design Patterns

### 3.1 Event-Driven Decoupling

Producers (agents) never reference consumers (MemoryAgent, other subscribers) directly. All coupling is through the event bus.

```
HypothesisAgent.run()
  └─ publish(RuntimeEvent(topic="hypothesis.generated", ...))
       └─ RuntimeEventBus._resolve_handlers("hypothesis.generated")
            └─ [MemoryAgent.handle_event, ...other subscribers]
```

This means:
- Adding a new subscriber never requires touching agent code
- Subscribers can be registered/deregistered at runtime
- Testing agents and subscribers is fully independent

**Topic Naming Convention:**
```
{domain}.{action}
hypothesis.generated
hypothesis.critiqued
synthesis.ready
coordination.started
coordination.complete
workflow.started
workflow.complete
```

Wildcard patterns supported:
- `hypothesis.*` — all hypothesis events
- `*` — all events (catch-all for logging, metrics)

### 3.2 Graceful Degradation Stack

Every external service is optional. The system implements a fallback chain:

```
Qdrant unavailable  → keyword-overlap scoring in ResearchMemory
Redis unavailable   → in-memory LRU for sessions, RuntimeEventBus for events
PostgreSQL unavail  → in-memory ring buffer for memory, skip persistence
Neo4j unavailable   → skip graph storage, continue without lineage
LLM unavailable     → heuristic hypothesis generation
Embeddings offline  → keyword fallback in ContextEngine
```

No service failure causes a hard crash. The system logs degraded state and continues.

### 3.3 Three-Phase Agent Lifecycle

All agents implement the same lifecycle:

```
perceive(context: dict) → dict     # structure input, recall prior context
reason(perception: dict) → dict    # apply domain logic (LLM or heuristic)
act(reasoning: dict) → dict        # format output, publish events, persist
run(context: dict) → AgentMessage  # orchestrates perceive → reason → act
```

This makes all agents:
- Testable independently per phase
- Observable with consistent OTel span names
- Replaceable without changing orchestration logic

### 3.4 Explicit Dependency Injection

No global mutable state. Every component receives its dependencies at construction:

```python
AgentCoordinator(
    event_bus=event_bus,
    hypothesis_agents=[HypothesisAgent(...), ...],
    critique_agents=[CritiqueAgent(...), ...],
    synthesis_agent=SynthesisAgent(...),
    inference_router=inference_router,
    research_memory=research_memory,
    config=CoordinatorConfig(),
)
```

`app.state` is the single injection point for the FastAPI application. All subsystem instances are created in `lifespan()` and mounted there.

### 3.5 Async-First Execution

All I/O operations are non-blocking:

```python
# Parallel agent execution
hypotheses = await asyncio.gather(*[
    agent.run({"question": q, "session_id": session_id})
    for q in sub_questions
])

# Parallel backend health check
results = await asyncio.gather(
    check_qdrant(), check_redis(), check_postgres(), check_neo4j(),
    return_exceptions=True
)
```

No `time.sleep()`, no blocking database calls, no synchronous HTTP inside cognition flows.

---

## 4. Data Flow Designs

### 4.1 Research Coordination Flow

```
POST /cognition/coordinate
  { "goal": "What causes superconductivity at room temperature?" }
         │
         ▼
AgentCoordinator.coordinate(goal, session_id)
  │
  ├─ 1. ResearchMemory.recall(goal)
  │      → [MemoryEntry, ...] (prior findings from Qdrant or ring buffer)
  │
  ├─ 2. _plan(goal) → ["sub_question_1", "sub_question_2", ...]
  │
  ├─ 3. asyncio.gather([HypothesisAgent.run(q) for q in sub_questions])
  │      Each HypothesisAgent:
  │        perceive() → injects prior_evidence, question
  │        reason()   → InferenceRouter.complete() or heuristic
  │        act()      → publishes "hypothesis.generated"
  │                       → MemoryAgent persists to ResearchMemory
  │
  ├─ 4. asyncio.gather([CritiqueAgent.run(hyp) for hyp in hypotheses])
  │      Each CritiqueAgent:
  │        publishes "hypothesis.critiqued"
  │
  └─ 5. SynthesisAgent.run(hypotheses + critiques)
         ReflectionEngine scores each hypothesis
         Selects best, synthesizes conclusion
         Publishes "synthesis.ready"
           → MemoryAgent persists to ResearchMemory

Response: CoordinatedResult {
  hypotheses: [...],
  critiques: [...],
  synthesis: "...",
  duration_seconds: 4.2,
  events_published: 7
}
```

### 4.2 Full Research Workflow Flow

```
POST /research/workflows
  { "goal": "..." }
         │
         ▼
ResearchWorkflow.run(goal)
  │
  ├─ 1. ResearchMemory.recall(goal) → prior_context
  ├─ 2. StreamManager.publish(wf_id, "planning_started")
  ├─ 3. _plan(goal, prior_context) → sub_questions[]
  ├─ 4. StreamManager.publish(wf_id, "planning_done")
  │
  ├─ 5. asyncio.gather([CognitivePipeline.run(q) for q in sub_questions])
  │      Each CognitivePipeline → ResearchAgent.run()
  │        ContextEngine.build(q) → semantic context packet
  │        Full hypothesis lifecycle (generate → evolve → reflect)
  │        ContradictionAnalyzer.analyze() if multiple hypotheses
  │        → SubQuestionResult
  │
  ├─ 6. _select_primary_hypothesis(sub_results)
  ├─ 7. Optional: DebateRuntime.run(primary_hyp, max_rounds=3)
  ├─ 8. Optional: RecursiveReasoningLoop.run(primary_hyp, config)
  │        Until: quality_threshold | no_improvement | max_depth
  │        GoldenBayesian updates confidence each iteration
  │
  ├─ 9. _synthesize_all(goal, all_results)
  ├─ 10. KnowledgeGraph.store_hypothesis(primary_hyp)
  └─ 11. StreamManager.publish(wf_id, "complete")

SSE stream: GET /streams/workflows/{id}
  → planning_started → planning_done → sub_question_complete (×N)
    → debate_complete → recursive_complete → synthesis_done → complete
```

### 4.3 Memory Storage Flow

```
MemoryEntry created by any agent
  │
  ▼
ResearchMemory.store(entry)
  ├─ _buffer.append(entry)          [always — in-memory ring buffer, 2000 cap]
  ├─ _store_postgres(entry)         [if session_factory available]
  │    INSERT INTO hypothesis_records (tenant_id, statement, confidence, ...)
  └─ _store_qdrant(entry)           [if context_engine available]
       EmbeddingProvider.embed(entry.statement) → vector
       QdrantClient.upsert(collection="research_hypotheses", vector=...)

ResearchMemory.recall(topic, limit=5)
  ├─ If Qdrant: ContextEngine.build(topic) → semantic search → [MemoryEntry]
  └─ Fallback: keyword overlap scoring over _buffer
```

### 4.4 Adaptive Cognition Flow

```
After each workflow execution:
  │
  ▼
QualityTracker.analyze(reasoning_trace)
  ├─ Gets recent trace entries
  ├─ Splits into first_half / second_half
  ├─ Computes avg quality score per half
  └─ Returns QualityReport {
       trend: "improving" | "stable" | "declining",
       avg_quality: 0.73,
       operation_stats: {...}
     }
  │
  ▼
AdaptiveConfigManager.adapt(quality_report)
  ├─ If improving: max_depth += 1, max_sub_questions += 1
  ├─ If declining: max_depth -= 1, max_sub_questions -= 1
  └─ Bounds: max_depth ∈ [2, 8], max_sub_questions ∈ [2, 8]

Updated config injected into next ResearchWorkflow / RecursiveReasoningLoop run
```

---

## 5. API Design

### 5.1 REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/metrics` | Prometheus metrics |
| POST | `/auth/login` | JWT token issuance |
| POST | `/auth/refresh` | Token refresh |
| POST | `/research/tasks` | Create async research task |
| GET | `/research/tasks/{id}` | Get task result |
| POST | `/research/workflows` | Run full research workflow |
| GET | `/research/workflows/{id}` | Get workflow result |
| POST | `/cognition/coordinate` | Run multi-agent coordination |
| GET | `/intelligence/report` | Get intelligence summary |
| GET | `/intelligence/recall` | Query memory by topic |
| GET | `/intelligence/hypotheses` | List stored hypotheses |
| GET | `/intelligence/agenda` | Get research agenda |
| POST | `/agenda/run` | Execute agenda item |
| GET | `/reasoning/traces` | List reasoning traces |
| GET | `/reasoning/traces/{id}` | Get single trace |
| GET | `/governance/audit` | Get audit log |
| POST | `/sessions` | Create cognitive session |
| GET | `/sessions/{id}` | Get session state |
| DELETE | `/sessions/{id}` | Close session |
| GET | `/streams/workflows/{id}` | SSE workflow progress |
| GET | `/runtime/status` | Runtime health and stats |
| GET | `/dashboard/metrics` | Dashboard summary metrics |

### 5.2 Middleware Stack (Request Order)

```
Incoming Request
    │
    ▼
SecurityMiddleware     ← X-API-Key validation (skip: /health, /metrics)
    │
    ▼
TenantMiddleware       ← Extract tenant_id from JWT
    │
    ▼
RateLimitMiddleware    ← Sliding window per client
    │
    ▼
QuotaMiddleware        ← Per-tenant quota enforcement
    │
    ▼
Route Handler          ← Business logic
```

### 5.3 SSE Response Format

```
GET /streams/workflows/{workflow_id}
Content-Type: text/event-stream

data: {"event": "planning_started", "workflow_id": "wf_123", "timestamp": "..."}

data: {"event": "planning_done", "sub_questions": 4, "timestamp": "..."}

data: {"event": "sub_question_complete", "index": 0, "question": "...", "timestamp": "..."}

data: {"event": "synthesis_done", "quality_score": 0.82, "timestamp": "..."}

data: {"event": "complete", "duration_seconds": 12.4, "timestamp": "..."}
```

---

## 6. Database Design

### 6.1 Core Tables

```sql
-- Tenants
tenants (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  domain TEXT UNIQUE NOT NULL,
  slug TEXT NOT NULL,
  tier TEXT DEFAULT 'free',  -- free | pro | enterprise
  status TEXT DEFAULT 'active',
  db_connection_string TEXT,
  encrypted_settings JSONB,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Users
users (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'member',
  is_active BOOLEAN DEFAULT true,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Research Tasks
research_tasks (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  question TEXT NOT NULL,
  status TEXT NOT NULL,  -- pending | running | complete | failed
  results JSONB,
  error_message TEXT,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Workflow Records
workflow_records (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  goal TEXT NOT NULL,
  status TEXT NOT NULL,
  sub_questions JSONB,
  results JSONB,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Hypothesis Records
hypothesis_records (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  statement TEXT NOT NULL,
  confidence FLOAT,
  topic TEXT,
  source TEXT,
  session_id TEXT,
  evidence JSONB,
  generation INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Reasoning Traces
reasoning_traces (
  id UUID PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  operation TEXT NOT NULL,
  input_hash TEXT,
  output_summary TEXT,
  agent_id TEXT,
  duration_seconds FLOAT,
  created_at TIMESTAMPTZ
)
```

### 6.2 Row-Level Security

All tables include RLS policies ensuring tenant isolation at the database level:

```sql
ALTER TABLE hypothesis_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON hypothesis_records
  FOR ALL USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

TenantMiddleware sets `app.tenant_id` on every connection from the JWT claim.

---

## 7. Event System Design

### 7.1 Topic Hierarchy

```
hypothesis.*
  ├─ hypothesis.generated
  └─ hypothesis.critiqued

synthesis.*
  └─ synthesis.ready

coordination.*
  ├─ coordination.started
  └─ coordination.complete

workflow.*
  ├─ workflow.started
  └─ workflow.complete

*  (catch-all)
```

### 7.2 RuntimeEvent Schema

```python
@dataclass
class RuntimeEvent:
    topic: str                     # e.g. "hypothesis.generated"
    payload: dict                  # event-specific data
    timestamp: datetime
    source_agent_id: str | None
    session_id: str | None
    correlation_id: str | None     # links related events
```

### 7.3 RedisEventBus Consumer Groups

```
Stream: irds:events:{topic}
Consumer Group: irds_consumer_group_{process_id}

XADD irds:events:hypothesis.generated * field1 val1 ...
XREADGROUP GROUP irds_consumer_group_1 consumer1 COUNT 10 STREAMS irds:events:hypothesis.generated >
XACK irds:events:hypothesis.generated irds_consumer_group_1 {message_id}
```

Each process creates its own consumer group, enabling fan-out delivery to all processes simultaneously.

---

## 8. Inference Routing Design

### 8.1 Tier Selection Logic

```
InferenceRouter.complete(prompt, system, tier="fast", auto_upgrade=True)
  │
  ├─ 1. _get_providers_by_tier(tier)
  │      filters providers where provider.reasoning_tier == tier and provider.enabled
  │
  ├─ 2. If no providers for tier and auto_upgrade:
  │      retry with complementary tier (fast→deep or deep→fast)
  │
  ├─ 3. For each provider in tier:
  │      response = await provider.complete(InferenceRequest(...))
  │      if response.text: return response.text
  │
  └─ 4. If all fail: log warning, return None (heuristic fallback triggered upstream)
```

### 8.2 Provider Registration

```python
providers = [
    OpenAIProvider(api_key=..., model="gpt-4-mini", tier="fast"),
    OpenAIProvider(api_key=..., model="gpt-4",      tier="deep"),
    GeminiProvider(api_key=..., model="gemini-1.5-flash", tier="fast"),
    GeminiProvider(api_key=..., model="gemini-1.5-pro",   tier="deep"),
    OllamaProvider(base_url=..., model="llama3.1",        tier="fast"),
]
router = InferenceRouter(providers=providers, reasoning_trace=trace)
```

---

## 9. Session Design

### 9.1 SessionState Schema

```python
@dataclass
class SessionState:
    session_id: str
    created_at: datetime
    updated_at: datetime
    goals: list[str]               # research goals added to session
    workflow_ids: list[str]        # workflows run in this session
    findings_count: int            # total knowledge entries accumulated
    status: str                    # active | closed
    metadata: dict                 # arbitrary session context
```

### 9.2 Persistence Strategy

```
CognitiveSessionManager
  ├─ Primary: Redis (24h TTL, JSON serialized)
  │    Key: "irds:session:{session_id}"
  └─ Fallback: In-memory LRU cache (100 sessions max)
       Used when Redis unavailable
```

---

## 10. Quality & Convergence Design

### 10.1 ReflectionEngine Scoring

```
score = strengths / (gaps + strengths)

Strengths detected (each +1):
  - contains "evidence" keyword
  - contains explicit confidence value
  - references prior findings
  - has structured reasoning

Gaps detected (each -1):
  - missing conclusion statement
  - no supporting evidence
  - contradicts prior findings
  - overconfident without justification
```

### 10.2 GoldenBayesian Confidence Update

```
φ = (1 + √5) / 2  ≈ 1.618 (golden ratio)

bayesian_factor = prior_confidence * (1 + evidence_weight)
golden_adjustment = iteration / φ
new_confidence = (bayesian_factor + golden_adjustment) / (1 + golden_adjustment)
new_confidence = min(0.98, max(0.1, new_confidence))
```

### 10.3 Convergence Conditions

```
RecursiveReasoningLoop terminates when ANY of:
  1. quality_score >= convergence_threshold (default 0.85)
  2. improvement < min_improvement (default 0.02) for two consecutive iterations
  3. depth >= max_depth (default configured by AdaptiveConfigManager)
  4. contradiction_detected AND quality declining
```

---

## 11. Deployment Design

### 11.1 Local Development Stack (Docker Compose)

```yaml
Services:
  api:        FastAPI + Uvicorn  :8000
  postgres:   PostgreSQL 15      :5432
  redis:      Redis 7            :6379
  qdrant:     Qdrant 1.7         :6333
  neo4j:      Neo4j 5            :7474 (HTTP), :7687 (Bolt)
  prometheus: Prometheus         :9090
```

### 11.2 Service Dependencies

```
api ─depends─▶ postgres, redis, qdrant, neo4j
             (all optional — degrades gracefully on absence)
```

### 11.3 Environment Variables

```bash
# Database
POSTGRES_URL=postgresql+asyncpg://user:pass@localhost:5432/irds
REDIS_URL=redis://localhost:6379/0
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM Providers
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-4-mini
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434

# Security
API_KEYS=key1,key2,key3
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_ENABLED=true

# Observability
LOG_LEVEL=INFO
```
