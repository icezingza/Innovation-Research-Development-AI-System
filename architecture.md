# Architecture Document
# Innovation Research & Development AI System (IRDS)

**Version:** 1.0  
**Date:** 2026-05-17  
**Status:** Phases 1–9 Complete

---

## 1. Architecture Overview

IRDS is a **layered distributed cognitive architecture** composed of eight distinct layers. Each layer has a single responsibility, explicit upward and downward dependencies, and communicates through defined interfaces — never through hidden side effects or shared mutable state.

```
┌───────────────────────────────────────────────────────────────────┐
│                        API LAYER                                  │
│    FastAPI · REST · SSE · Auth Middleware · Rate Limiting         │
├───────────────────────────────────────────────────────────────────┤
│                   ORCHESTRATION LAYER                             │
│    AgentCoordinator · ResearchWorkflow · DebateRuntime            │
│    RecursiveReasoningLoop · ResearchAgenda · CognitivePipeline    │
├───────────────────────────────────────────────────────────────────┤
│                      AGENT LAYER                                  │
│    BaseAgent · HypothesisAgent · CritiqueAgent · SynthesisAgent  │
│    ResearchAgent · MemoryAgent (ReactiveSubscriber)               │
├───────────────────────────────────────────────────────────────────┤
│                  REASONING & COGNITION LAYER                      │
│    ReflectionEngine · HypothesisEvolutionEngine                   │
│    ContradictionAnalyzer · QualityTracker                         │
│    AdaptiveConfigManager · GoldenBayesian · ReasoningTrace        │
├───────────────────────────────────────────────────────────────────┤
│                  INFRASTRUCTURE LAYER                             │
│    RuntimeEventBus · RedisEventBus · AsyncScheduler               │
│    AsyncWorkerPool · CognitiveSessionManager                      │
│    AgentSpawner · StreamManager · RuntimeStateManager             │
├───────────────────────────────────────────────────────────────────┤
│                     MEMORY LAYER (4-tier)                         │
│  ┌──────────────┬──────────────┬───────────────┬───────────────┐ │
│  │  In-Memory   │   Qdrant     │   Neo4j        │  PostgreSQL   │ │
│  │  Ring Buffer │  (Vector)    │  (Graph)       │  (Relational) │ │
│  │  2000 entries│  Embeddings  │  Lineage Graph │  Full Records │ │
│  └──────────────┴──────────────┴───────────────┴───────────────┘ │
│    ResearchMemory · ContextEngine · KnowledgeGraph                │
│    Redis (runtime state, traces, audit, events, sessions)         │
├───────────────────────────────────────────────────────────────────┤
│                GOVERNANCE & SECURITY LAYER                        │
│    PolicyEnforcer · GovernanceAuditLog · APIKeyManager            │
│    RateLimiter · TenantContext · QuotaService · RLS Policies      │
├───────────────────────────────────────────────────────────────────┤
│                    INFERENCE LAYER                                │
│    InferenceRouter · OpenAIProvider · GeminiProvider              │
│    DeepSeekProvider · OllamaProvider · EmbeddingProvider          │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Specifications

### 2.1 API Layer (`src/api/`)

**Responsibility:** HTTP interface, authentication, middleware orchestration, and application lifecycle management.

**Components:**
- `main.py` — `create_app()` factory, `lifespan()` context manager
- `routers/` — 13 separate router modules (auth, research, workflows, cognition, etc.)
- `middleware/` — SecurityMiddleware, TenantMiddleware, RateLimitMiddleware, QuotaMiddleware

**Application Lifecycle (`lifespan`):**
```
Startup:
  1. Probe all external services (Qdrant, Redis, PostgreSQL, Neo4j)
  2. Create inference providers (from env vars)
  3. Create InferenceRouter with available providers
  4. Create EmbeddingProvider (local always available)
  5. Create all memory backends (degraded if unavailable)
  6. Create ResearchMemory, ContextEngine, KnowledgeGraph
  7. Create agents (HypothesisAgent, CritiqueAgent, SynthesisAgent, ResearchAgent)
  8. Create MemoryAgent, register with EventBus
  9. Create AgentCoordinator, ResearchWorkflow, CognitivePipeline
  10. Create AsyncScheduler, AsyncWorkerPool
  11. Create CognitiveSessionManager
  12. Create PolicyEnforcer, GovernanceAuditLog
  13. Create ReasoningTrace, QualityTracker, AdaptiveConfigManager
  14. Mount everything onto app.state
  15. Start AsyncWorkerPool

Shutdown:
  1. Cancel all running tasks
  2. Close database connections
  3. Close Redis connections
  4. Close Qdrant connections
  5. Close Neo4j driver
```

**Middleware Execution Order:**
```
Request → SecurityMiddleware → TenantMiddleware → RateLimitMiddleware → QuotaMiddleware → Route
Response ← SecurityMiddleware ← TenantMiddleware ← RateLimitMiddleware ← QuotaMiddleware ← Route
```

**Key Invariants:**
- Routes never contain business logic — they extract args and call service methods
- All dependencies injected via `request.app.state`
- Exemptions from auth: `/health`, `/metrics`

---

### 2.2 Orchestration Layer (`src/orchestration/`)

**Responsibility:** Coordinate multiple agents, manage workflow state, implement research strategies.

**Components:**

| Class | Responsibility |
|-------|---------------|
| `AgentCoordinator` | Parallel hypothesis + critique + synthesis pipeline |
| `ResearchWorkflow` | Full autonomous research workflow (plan→debate→recurse→synthesize) |
| `CognitivePipeline` | Single sub-question pipeline using ResearchAgent |
| `DebateRuntime` | Multi-round hypothesis debate system |
| `RecursiveReasoningLoop` | Iterative convergence-based hypothesis refinement |
| `ResearchAgenda` | Gap detection and autonomous agenda generation |

**Dependency Graph:**
```
ResearchWorkflow
  ├─ uses: AgentCoordinator (for synthesis phases)
  ├─ uses: CognitivePipeline (per sub-question)
  ├─ uses: DebateRuntime (optional debate phase)
  ├─ uses: RecursiveReasoningLoop (optional recursion phase)
  ├─ uses: ResearchMemory (for recall)
  ├─ uses: KnowledgeGraph (for lineage storage)
  ├─ uses: StreamManager (for SSE progress)
  └─ uses: PolicyEnforcer (for governance gates)

AgentCoordinator
  ├─ uses: HypothesisAgent, CritiqueAgent, SynthesisAgent
  ├─ uses: ResearchMemory (for prior context)
  └─ uses: RuntimeEventBus (publishing coordination events)
```

**Invariant:** Orchestration never imports from `memory/` internals directly — always through the `ResearchMemory` facade.

---

### 2.3 Agent Layer (`src/agents/`)

**Responsibility:** Implement specific cognitive capabilities. Each agent is a single-responsibility cognitive unit.

**Components:**

| Agent | Lifecycle Role | Primary Output |
|-------|---------------|----------------|
| `HypothesisAgent` | Generates initial hypothesis for a sub-question | `hypothesis.generated` event |
| `CritiqueAgent` | Stress-tests hypothesis, identifies weaknesses | `hypothesis.critiqued` event |
| `SynthesisAgent` | Synthesizes multiple hypotheses into conclusion | `synthesis.ready` event |
| `ResearchAgent` | Full lifecycle agent: generate + evolve + reflect | SubQuestionResult |
| `MemoryAgent` | ReactiveSubscriber: persists findings to memory | Side-effect only |

**BaseAgent Interface:**
```python
class BaseAgent(ABC):
    agent_id: str
    agent_type: str
    inference_router: InferenceRouter | None
    event_bus: RuntimeEventBus | None
    governance: PolicyEnforcer | None

    @abstractmethod
    async def perceive(self, context: dict) -> dict: ...

    @abstractmethod
    async def reason(self, perception: dict) -> dict: ...

    @abstractmethod
    async def act(self, reasoning: dict) -> dict: ...

    async def run(self, context: dict) -> AgentMessage:
        # wraps perceive→reason→act with OTel tracing + Prometheus metrics
```

**Message Protocol:**
```python
@dataclass
class AgentMessage:
    id: str
    sender_id: str
    message_type: MessageType  # ACTION | OBSERVATION | QUERY | RESPONSE
    content: dict
    timestamp: datetime
```

**Invariant:** Agents never import from `orchestration/` — dependency flows downward only.

---

### 2.4 Reasoning & Cognition Layer (`src/reasoning/`, `src/research/`)

**Responsibility:** Implement the cognitive algorithms that drive hypothesis quality, evolution, and convergence.

**Components:**

| Class | Role |
|-------|------|
| `ReflectionEngine` | Scores reasoning quality, detects gaps and strengths |
| `HypothesisEvolutionEngine` | Refines hypothesis text through generational improvement |
| `ContradictionAnalyzer` | Detects logical inconsistencies between hypotheses |
| `QualityTracker` | Analyzes reasoning trace trends (improving/stable/declining) |
| `AdaptiveConfigManager` | Adjusts RecursiveConfig + WorkflowConfig based on QualityTracker |
| `GoldenBayesian` | Bayesian confidence update scaled by golden ratio |
| `ReasoningTrace` | 3-tier trace recording (memory → Redis → PostgreSQL) |

**Feedback Loop:**
```
ReasoningTrace.record(entry)
       │
       ▼
QualityTracker.analyze(trace)
       │
       ▼
AdaptiveConfigManager.adapt(quality_report)
  ├─ Adjusts RecursiveConfig (max_depth)
  └─ Adjusts WorkflowConfig (max_sub_questions)
       │
       ▼
Next workflow execution uses updated config
```

**Invariant:** Reasoning layer never calls agents or orchestration — it is a pure computational layer providing analysis and configuration.

---

### 2.5 Infrastructure Layer (`src/infrastructure/`, `src/runtime/`)

**Responsibility:** Provide the runtime substrate: scheduling, concurrency, session management, event distribution, and real-time streaming.

**Components:**

| Class | Role |
|-------|------|
| `RuntimeEventBus` | In-memory async pub/sub with wildcard topic matching |
| `RedisEventBus` | Extends RuntimeEventBus with Redis Streams for cross-process delivery |
| `AsyncScheduler` | Priority heap (TaskPriority 1–10) with cancellation |
| `AsyncWorkerPool` | Bounded concurrency pool draining the scheduler |
| `CognitiveSessionManager` | Redis-backed session state with LRU fallback |
| `AgentSpawner` | Runtime agent creation and coordinator injection |
| `StreamManager` | SSE event publisher for workflow progress |
| `RuntimeStateManager` | Singleton container for app.state injection |

**Event Bus Topic Resolution:**
```
publish("hypothesis.generated")
  → exact match: "hypothesis.generated"
  → prefix match: "hypothesis.*"
  → catch-all: "*"
  → execute all matched handlers concurrently
  → isolate failures per handler (one crash doesn't stop others)
```

**Worker Pool Execution:**
```
AsyncWorkerPool(max_workers=4, scheduler=scheduler)
  ├─ worker_0: await scheduler.execute_next()
  ├─ worker_1: await scheduler.execute_next()
  ├─ worker_2: await scheduler.execute_next()
  └─ worker_3: await scheduler.execute_next()
  All idle-wait when queue empty, wake on new task submission
```

---

### 2.6 Memory Layer (`src/memory/`)

**Responsibility:** Provide multi-tier persistent cognitive storage with consistent read/write interfaces.

**4-Tier Architecture:**

```
Tier 0: In-Memory Ring Buffer (always available)
  └─ 2000 entry cap, FIFO eviction
  └─ Used for: fallback recall, fast recent-history access

Tier 1: Redis (runtime cache + streams)
  └─ SessionState (24h TTL)
  └─ ReasoningTrace cache (24h TTL)
  └─ GovernanceAuditLog entries
  └─ Event streams (XADD/XREADGROUP)

Tier 2: PostgreSQL (structured persistence)
  └─ research_tasks, workflow_records
  └─ hypothesis_records, reasoning_traces
  └─ tenants, users
  └─ Alembic-managed schema

Tier 3: Qdrant (vector semantic memory)
  └─ Collection: research_hypotheses
  └─ 384-dim vectors (all-MiniLM-L6-v2)
  └─ Cosine similarity search
  └─ Used for: ContextEngine semantic recall

Tier 4: Neo4j (graph lineage)
  └─ Hypothesis nodes with generation counter
  └─ EVOLVED_FROM edges between generations
  └─ CONTRADICTS edges from ContradictionAnalyzer
  └─ Used for: lineage visualization, contradiction tracking
```

**Facade Classes:**

| Class | Abstracts | Interface |
|-------|-----------|-----------|
| `ResearchMemory` | All 4 tiers | `store()`, `recall()`, `get_all()`, `stats()` |
| `ContextEngine` | Qdrant + EmbeddingProvider | `build(topic)` → ContextPacket |
| `KnowledgeGraph` | Neo4j | `store_hypothesis()`, `get_lineage()` |
| `MemoryManager` | All backends | `healthcheck()` → {vector, graph, runtime, persistence} |

---

### 2.7 Governance & Security Layer (`src/governance/`, `src/security/`, `src/tenants/`)

**Responsibility:** Enforce policy, authenticate requests, isolate tenants, and provide audit trails for all agent actions.

**Components:**

| Class | Role |
|-------|------|
| `PolicyEnforcer` | Evaluates AgentMessage against policy rules, returns ALLOW/DENY/WARN |
| `GovernanceAuditLog` | Append-only audit log (in-memory + Redis) for every policy decision |
| `APIKeyManager` | X-API-Key header validation with constant-time comparison |
| `RateLimiter` | Sliding-window rate limiting per client |
| `TenantContext` | FastAPI dependency extracting tenant_id from JWT |
| `TenantMiddleware` | Sets `app.tenant_id` on DB connection for RLS |
| `QuotaService` | Per-tenant API call and storage quota enforcement |

**Governance Decision Flow:**
```
AgentCoordinator.coordinate()
  ├─ PolicyEnforcer.enforce(agent_message)
  │    ├─ If ALLOW: continue pipeline
  │    ├─ If WARN: log warning, continue
  │    └─ If DENY: raise PolicyViolationError
  │         → GovernanceAuditLog.append(decision_entry)
  └─ (continue only if allowed)
```

**Invariant:** Governance layer is never bypassed — all cognitive actions flow through PolicyEnforcer. No agent can call inference or mutate memory without a governance gate upstream.

---

### 2.8 Inference Layer (`src/inference/`)

**Responsibility:** Provide a unified, observable, fault-tolerant interface to all LLM providers.

**Components:**

| Class | Role |
|-------|------|
| `InferenceRouter` | Selects provider by tier, falls back on failure |
| `OpenAIProvider` | OpenAI-compatible API (OpenAI, OpenRouter, vLLM) |
| `GeminiProvider` | Google Gemini (flash/pro) |
| `DeepSeekProvider` | DeepSeek API |
| `OllamaProvider` | Local Ollama inference |
| `EmbeddingProvider` | Sentence Transformers or OpenAI embeddings |

**Provider Tier Model:**
```
fast tier: gpt-4-mini, gemini-1.5-flash, ollama/llama3.1, deepseek-chat
deep tier: gpt-4, gemini-1.5-pro, deepseek-reasoner

Routing:
  InferenceRouter.complete(prompt, tier="fast")
    → try all fast providers in order
    → if all fail and auto_upgrade=True: try deep providers
    → if all fail: return None (heuristic fallback)
```

**Observability:**
- Every call logged to ReasoningTrace (provider, model, tier, latency, success)
- Token usage tracked per provider
- Failed providers logged at WARN level for operator visibility

---

## 3. Cross-Cutting Concerns

### 3.1 Observability Architecture

```
Every agent cycle:
  OTel span: agent.{agent_id}.cycle
    attributes: agent_type, session_id, input_hash

Every inference call:
  OTel span: inference.{provider}.complete
    attributes: provider, model, tier, latency_ms, success

Every orchestration flow:
  OTel span: orchestration.{workflow_type}
    attributes: goal_hash, sub_question_count, duration_ms

Prometheus metrics:
  irds_active_agents_total (gauge)
  irds_reasoning_latency_seconds (histogram)
  irds_runtime_events_total (counter, label: event_type)
  irds_hypothesis_quality (histogram)
  irds_memory_recall_latency_seconds (histogram)
```

### 3.2 Error Handling Architecture

```
Domain Errors (raised explicitly):
  PolicyViolationError     ← governance.py
  AgentExecutionError      ← agents/base.py
  InferenceRouterError     ← inference/router.py
  MemoryBackendError       ← memory/*.py

Pattern for all errors:
  1. Log structured error with context
  2. Emit metric (error counter by type)
  3. Propagate with domain-specific exception
  4. Never silently swallow
```

### 3.3 Testing Architecture

```
tests/
  ├── unit/
  │   ├── test_agent.py                   ← BaseAgent lifecycle
  │   ├── test_specialized_agents.py      ← HypothesisAgent, CritiqueAgent, SynthesisAgent
  │   ├── test_event_bus.py               ← RuntimeEventBus pub/sub
  │   ├── test_redis_event_bus.py         ← RedisEventBus with mock Redis
  │   ├── test_reasoning.py              ← ReflectionEngine, Evolution
  │   ├── test_recursive_reasoning.py     ← RecursiveReasoningLoop convergence
  │   ├── test_memory_agent.py            ← MemoryAgent event subscription
  │   ├── test_research_memory.py        ← ResearchMemory 3-tier storage
  │   ├── test_runtime.py                ← AsyncScheduler, WorkerPool
  │   ├── test_scheduler.py              ← Priority queue correctness
  │   ├── test_worker_pool.py            ← Bounded concurrency
  │   ├── test_cognitive_session.py      ← CognitiveSessionManager
  │   ├── test_governance.py             ← PolicyEnforcer decisions
  │   ├── test_security.py               ← APIKeyManager, RateLimiter
  │   ├── test_quality_tracker.py        ← Trend detection
  │   ├── test_adaptive_config.py        ← Auto-tuning
  │   └── test_research_agenda.py       ← Gap detection
  ├── integration/
  │   ├── test_agent_coordinator.py      ← Full coordination pipeline
  │   ├── test_cognitive_pipeline*.py    ← Pipeline + governance
  │   └── test_api.py                   ← API routes
  └── test_tenants.py                   ← Multi-tenancy isolation
```

**Coverage:** 207 tests, 0 failures, 0 lint errors

---

## 4. Module Dependency Rules

```
Allowed dependency directions (→ means "may import from"):

api          → orchestration, runtime, memory, governance, inference, security, tenants
orchestration → agents, reasoning, memory, infrastructure, governance, inference
agents       → reasoning, memory, infrastructure, inference, protocols
reasoning    → memory (read-only), inference
infrastructure → (no upward imports — foundational)
memory       → infrastructure (Redis only)
governance   → infrastructure, protocols
inference    → (no upward imports — foundational)
security     → infrastructure
tenants      → (no upward imports — data layer)
protocols    → (no imports — pure contracts)
telemetry    → (no upward imports — side-effect only)

Forbidden:
  reasoning  → agents (must NOT)
  memory     → orchestration (must NOT)
  inference  → agents (must NOT)
  agents     → orchestration (must NOT)
  governance → agents (governance is a gate, not a controller)
```

---

## 5. Source Tree

```
src/
├── agents/
│   ├── base_agent.py              BaseAgent ABC + OTel wrapping
│   ├── hypothesis_agent.py        Hypothesis generation
│   ├── critique_agent.py          Hypothesis critique
│   ├── synthesis_agent.py         Multi-hypothesis synthesis
│   ├── research_agent.py          Full lifecycle research
│   └── memory_agent.py            ReactiveSubscriber persistence
│
├── api/
│   ├── main.py                    create_app(), lifespan()
│   ├── middleware/
│   │   ├── security.py            X-API-Key enforcement
│   │   ├── tenant.py              Tenant context extraction
│   │   ├── rate_limit.py          Sliding-window rate limiting
│   │   └── quota.py               Per-tenant quota enforcement
│   └── routers/
│       ├── auth.py                Login, token, refresh
│       ├── research.py            Task creation and retrieval
│       ├── workflows.py           Workflow execution
│       ├── cognition.py           Multi-agent coordination
│       ├── intelligence.py        Memory recall + reports
│       ├── reasoning.py           Trace access
│       ├── governance.py          Audit log access
│       ├── sessions.py            Cognitive session management
│       ├── agenda.py              Research agenda
│       ├── runtime.py             Runtime status
│       ├── streams.py             SSE workflow progress
│       ├── dashboard.py           Metrics summary
│       ├── tenants.py             Tenant provisioning
│       └── health.py              Liveness check
│
├── orchestration/
│   ├── agent_coordinator.py       Parallel hypothesis pipeline
│   ├── research_workflow.py       Full autonomous workflow
│   ├── cognitive_pipeline.py      Single sub-question pipeline
│   ├── debate_runtime.py          Multi-round debate
│   └── research_agenda.py        Gap detection + agenda
│
├── reasoning/
│   ├── reasoning_trace.py         3-tier trace recording
│   ├── reflection_engine.py       Quality scoring + gap detection
│   ├── hypothesis_evolution.py    Generational hypothesis refinement
│   ├── contradiction_analyzer.py  Logical contradiction detection
│   ├── quality_tracker.py         Trend analysis
│   ├── adaptive_config.py         Auto-tuning manager
│   └── recursive_loop.py          Convergence-based iteration
│
├── memory/
│   ├── research_memory.py         3-tier accumulation facade
│   ├── context_engine.py          Semantic context builder
│   ├── knowledge_graph.py         Neo4j lineage tracking
│   ├── memory_manager.py          Unified health + routing
│   ├── qdrant_connector.py        Qdrant client + operations
│   ├── neo4j_connector.py         Neo4j driver + queries
│   ├── postgres_store.py          asyncpg pool + queries
│   └── redis_store.py             Redis client + TTL operations
│
├── infrastructure/
│   ├── event_bus.py               RuntimeEventBus + RedisEventBus
│   └── reactive_subscriber.py     ReactiveSubscriber ABC
│
├── runtime/
│   ├── scheduler.py               Priority heap scheduler
│   ├── worker_pool.py             Bounded concurrency pool
│   ├── session_manager.py         CognitiveSessionManager
│   ├── state_manager.py           RuntimeStateManager
│   ├── agent_spawner.py           Dynamic agent creation
│   └── stream_manager.py          SSE publisher
│
├── inference/
│   ├── router.py                  InferenceRouter (tier selection)
│   ├── openai_provider.py         OpenAI-compatible provider
│   ├── gemini_provider.py         Google Gemini provider
│   ├── deepseek_provider.py       DeepSeek provider
│   ├── ollama_provider.py         Ollama local provider
│   └── embedding_provider.py      Sentence Transformers + OpenAI
│
├── governance/
│   ├── policy_enforcer.py         ALLOW/DENY/WARN decisions
│   └── audit_log.py               Append-only audit log
│
├── security/
│   ├── api_key_manager.py         X-API-Key validation
│   └── rate_limiter.py            Sliding-window limiter
│
├── tenants/
│   ├── models.py                  Tenant, User, TenantMember
│   ├── context.py                 TenantContext FastAPI dependency
│   ├── middleware.py              TenantMiddleware
│   └── quota.py                  QuotaService
│
├── protocols/
│   └── agent_message.py          AgentMessage, MessageType contracts
│
├── telemetry/
│   ├── metrics.py                Prometheus metric definitions
│   └── tracing.py               OpenTelemetry tracer setup
│
└── config.py                     Settings (pydantic-settings, env vars)
```

---

## 6. Scalability Path

### Current (Phase 9): Single Process
```
Single uvicorn process
  AsyncWorkerPool (N concurrent tasks)
  RuntimeEventBus (in-process pub/sub)
  Redis (optional, used for sessions + traces)
```

### Near-term: Multi-Process
```
Multiple uvicorn workers (gunicorn -w 4)
  RedisEventBus (cross-process event delivery)
  Redis (shared sessions + traces)
  Shared PostgreSQL + Qdrant + Neo4j
```

### Long-term: Distributed
```
Kubernetes deployment
  Horizontal agent worker pools
  Celery or custom worker queues via Redis Streams
  Dedicated reasoning microservice
  Read replicas for PostgreSQL
  Qdrant cluster mode
  Neo4j causal cluster
```

---

## 7. Key Architectural Decisions

### ADR-001: Event Bus Decoupling
**Decision:** Producers publish to event bus topics; consumers register independently.  
**Rationale:** Eliminates coupling between HypothesisAgent and MemoryAgent. New subscribers added without touching agent code.  
**Trade-off:** Debugging event flows requires trace correlation IDs, not simple call stacks.

### ADR-002: 4-Tier Memory with Graceful Degradation
**Decision:** ResearchMemory writes to all available backends; reads fall back down the tier stack.  
**Rationale:** System operates fully in heuristic mode with only in-memory tier. Production adds persistence tiers incrementally.  
**Trade-off:** Data consistency is eventual, not transactional across tiers.

### ADR-003: Governance as Gateway
**Decision:** PolicyEnforcer gates all agent pipeline execution before any inference or memory mutation.  
**Rationale:** No agent action can bypass governance. Audit trail is complete and append-only.  
**Trade-off:** Every coordination incurs one governance check overhead (~1ms in-memory).

### ADR-004: Async-First Throughout
**Decision:** All I/O, database, inference, and event operations are async with asyncio.  
**Rationale:** Enables parallelism in orchestration (asyncio.gather for agents) without threading complexity.  
**Trade-off:** Synchronous callers must use asyncio.run(); no sync entry points exposed.

### ADR-005: Pluggable Inference Providers
**Decision:** InferenceRouter selects providers by tier; new providers implement BaseInferenceProvider.  
**Rationale:** Enables switching models without changing agent or orchestration code.  
**Trade-off:** Provider-specific features (tool use, function calling) not exposed through unified interface.

### ADR-006: Multi-Tenancy via PostgreSQL RLS
**Decision:** Tenant isolation enforced at database layer via Row-Level Security policies.  
**Rationale:** Tenant data separation is guaranteed even if application-layer bugs exist.  
**Trade-off:** Requires PostgreSQL; tenant_id must be set on every connection via middleware.
