# Tasks & Roadmap
# Innovation Research & Development AI System (IRDS)

**Version:** 1.0  
**Date:** 2026-05-17  
**Current Phase:** 9 Complete — Cognitive Operating System Active

---

## Phase Status Summary

| Phase | Name | Status | Tests |
|-------|------|--------|-------|
| 1 | Core Runtime Foundation | ✅ Complete | Passing |
| 2 | Knowledge Infrastructure | ✅ Complete | Passing |
| 3 | Multi-Agent Coordination | ✅ Complete | Passing |
| 4 | Persistent Semantic Runtime | ✅ Complete | Passing |
| 5 | Security & Hardening | ✅ Complete | Passing |
| 6 | Distributed Execution | ✅ Complete | Passing |
| 7 | Adaptive Cognition | ✅ Complete | Passing |
| 8 | Autonomous Research Agenda | ✅ Complete | Passing |
| 9 | Cognitive Operating System | ✅ Complete | Passing |
| 10 | Distributed Worker Scaling | 🔲 Planned | — |
| 11 | Advanced Cognition | 🔲 Planned | — |
| 12 | Scientific Autonomy | 🔲 Planned | — |

**Current:** 207 tests, 0 failures, 0 lint errors

---

## Completed Phases (1–9)

---

### Phase 1 — Core Runtime Foundation

**Goal:** Establish foundational async runtime with modular agents, inference abstraction, and event-driven architecture.

**Delivered:**
- [x] `BaseAgent` ABC with perceive → reason → act lifecycle
- [x] `HypothesisAgent`, `CritiqueAgent`, `SynthesisAgent` implementations
- [x] `RuntimeEventBus` with async pub/sub and wildcard topic matching
- [x] `InferenceRouter` with tier-based provider selection
- [x] `OpenAIProvider`, `OllamaProvider` implementations
- [x] `AgentMessage` and `MessageType` protocol contracts
- [x] `AsyncScheduler` with priority heap (TaskPriority 1–10)
- [x] `AsyncWorkerPool` bounded concurrency
- [x] Prometheus metrics: `irds_active_agents_total`, `irds_runtime_events_total`
- [x] FastAPI application skeleton with lifespan management
- [x] `/health`, `/metrics` endpoints
- [x] Basic test suite (agents, event bus, scheduler)

---

### Phase 2 — Knowledge Infrastructure

**Goal:** Add persistent knowledge storage with vector search and graph lineage tracking.

**Delivered:**
- [x] `Qdrant` connector with `research_hypotheses` collection
- [x] `EmbeddingProvider` (local `all-MiniLM-L6-v2` + OpenAI remote)
- [x] `ContextEngine` for semantic context packet generation
- [x] `KnowledgeGraph` (Neo4j) for hypothesis lineage and contradiction edges
- [x] `ResearchMemory` facade (in-memory ring buffer + Qdrant + PostgreSQL)
- [x] `MemoryManager` with unified healthcheck
- [x] Alembic migrations for `hypothesis_records`, `research_tasks`, `workflow_records`
- [x] `ResearchWorkflow` — plan → research → synthesis end-to-end
- [x] `MemoryAgent` as ReactiveSubscriber for event-driven persistence
- [x] Docker Compose with PostgreSQL, Redis, Qdrant, Neo4j, Prometheus

---

### Phase 3 — Multi-Agent Coordination

**Goal:** Implement parallel multi-agent research coordination with debate and orchestration.

**Delivered:**
- [x] `AgentCoordinator` — parallel hypothesis + critique + synthesis pipeline
- [x] `CognitivePipeline` — single sub-question research pipeline using ResearchAgent
- [x] `DebateRuntime` — multi-round hypothesis debate system
- [x] `ResearchAgent` — full lifecycle agent (generate → evolve → reflect)
- [x] `HypothesisEvolutionEngine` — generational hypothesis refinement
- [x] `ReflectionEngine` — quality scoring and gap detection
- [x] `ContradictionAnalyzer` — logical contradiction detection
- [x] `AgentSpawner` — runtime agent creation and coordinator injection
- [x] `/cognition/coordinate` API endpoint
- [x] `/research/workflows` API endpoint with full workflow execution
- [x] Coordination events: `coordination.started`, `coordination.complete`

---

### Phase 4 — Persistent Semantic Runtime

**Goal:** Cross-session memory continuity, semantic reasoning, and SSE streaming.

**Delivered:**
- [x] `ReasoningTrace` — 3-tier trace recording (memory → Redis → PostgreSQL)
- [x] `RecursiveReasoningLoop` — convergence-based iterative refinement
- [x] `GoldenBayesian` — golden ratio + Bayesian confidence updates
- [x] `CognitiveSessionManager` — Redis-backed sessions with LRU fallback
- [x] `StreamManager` — SSE publisher for workflow progress
- [x] `/streams/workflows/{id}` SSE endpoint
- [x] `/sessions` CRUD endpoints
- [x] Cross-session recall via ResearchMemory.recall()
- [x] `reasoning_traces` table and Alembic migration
- [x] Prior context injection into agent perception phase

---

### Phase 5 — Security & Hardening

**Goal:** Production-grade authentication, rate limiting, multi-tenancy, and governance.

**Delivered:**
- [x] `APIKeyManager` — X-API-Key validation with constant-time comparison
- [x] `RateLimiter` — sliding window per-client (60 req/min default)
- [x] `SecurityMiddleware` — auth enforcement with exemptions (/health, /metrics)
- [x] `PolicyEnforcer` — ALLOW/DENY/WARN decisions for all agent messages
- [x] `GovernanceAuditLog` — append-only policy decision log
- [x] JWT authentication (`/auth/login`, `/auth/refresh`)
- [x] `TenantContext` FastAPI dependency for tenant_id extraction
- [x] `TenantMiddleware` for DB-level tenant context
- [x] PostgreSQL Row-Level Security policies on all tables
- [x] `tenants`, `users` tables and migrations
- [x] `QuotaService` for per-tenant quota enforcement
- [x] `/governance/audit` endpoint

---

### Phase 6 — Distributed Execution

**Goal:** Redis-backed event streams enabling cross-process event distribution.

**Delivered:**
- [x] `RedisEventBus` — extends RuntimeEventBus with Redis Streams (XADD/XREADGROUP)
- [x] Consumer group per process with exactly-once delivery
- [x] `create_event_bus(redis_client)` factory — Redis when available, in-memory fallback
- [x] `RedisRateLimiter` for distributed rate limiting
- [x] Session TTL and cleanup via Redis TTL
- [x] `GeminiProvider`, `DeepSeekProvider` inference providers added
- [x] Multi-provider InferenceRouter with auto-upgrade between tiers
- [x] `/runtime/status` endpoint for runtime health visibility
- [x] All agents migrated to use create_event_bus() factory

---

### Phase 7 — Adaptive Cognition

**Goal:** Self-tuning cognitive infrastructure that improves reasoning quality over time.

**Delivered:**
- [x] `QualityTracker` — trend detection (improving / stable / declining) from ReasoningTrace
- [x] `AdaptiveConfigManager` — auto-tunes RecursiveConfig.max_depth and WorkflowConfig.max_sub_questions
- [x] Adaptive bounds: max_depth ∈ [2, 8], max_sub_questions ∈ [2, 8]
- [x] `QualityReport` with per-operation statistics
- [x] Integration of AdaptiveConfigManager into ResearchWorkflow
- [x] `irds_hypothesis_quality` Prometheus histogram
- [x] OpenTelemetry spans for reasoning quality operations
- [x] Tests: `test_quality_tracker.py`, `test_adaptive_config.py`

---

### Phase 8 — Autonomous Research Agenda

**Goal:** System autonomously identifies research gaps and prioritizes next investigations.

**Delivered:**
- [x] `ResearchAgenda` — scans ResearchMemory for gaps
  - Low-confidence topics (< 0.55 avg) flagged as research gaps
  - Sparse topics (< 3 entries) flagged as research gaps
  - Priority computed as: 10 - (avg_confidence * 5 + entry_count * 0.5)
- [x] `AgendaItem` schema: {topic, gap_reason, priority, suggested_questions[]}
- [x] `/intelligence/agenda` GET endpoint
- [x] `/agenda/run` POST endpoint for executing agenda items
- [x] `/intelligence/report` for combined intelligence summary
- [x] `/intelligence/recall` for topic-based memory recall
- [x] Tests: `test_research_agenda.py`

---

### Phase 9 — Cognitive Operating System

**Goal:** Full cognitive OS with persistent agent identities, dynamic spawning, and multi-tenant isolation.

**Delivered:**
- [x] `CognitiveSessionManager` enhanced with goal tracking and findings accumulation
- [x] `AgentSpawner` with runtime injection into live `AgentCoordinator`
- [x] `RuntimeStateManager` for centralized app.state management
- [x] Frontend React dashboard (`frontend/`) with Vite build
- [x] `/dashboard/metrics` endpoint for operational metrics
- [x] Full multi-tenant API with tenant provisioning
- [x] `swarms/` — pre-built swarm templates for common research patterns
- [x] `auth/` — JWT auth module
- [x] `billing/` — billing model stubs
- [x] 207 total tests, all passing
- [x] 0 ruff lint errors

---

## Planned Phases (10–12)

---

### Phase 10 — Distributed Worker Scaling

**Goal:** Horizontal scaling of agent workers across multiple hosts and processes.

**Planned Tasks:**
- [ ] Extract agent execution into standalone worker processes
- [ ] Implement task distribution via Redis Streams job queue
- [ ] Worker heartbeat and health monitoring
- [ ] Worker auto-scaling based on queue depth
- [ ] Distributed ReasoningTrace with cross-host correlation
- [ ] Leader election for AgentCoordinator (using Redis locks)
- [ ] Kubernetes deployment manifests with HPA
- [ ] Worker pool metrics: queue_depth, worker_utilization, task_latency
- [ ] Integration tests for multi-worker coordination
- [ ] Documentation: horizontal scaling guide

**Success Criteria:**
- System processes 3× current workflow throughput with 3 worker nodes
- No cognitive state loss during worker restart
- Queue depth telemetry visible in Prometheus

---

### Phase 11 — Advanced Cognition

**Goal:** More sophisticated reasoning strategies: hypothesis tournaments, temporal reasoning, multi-iteration debate.

**Planned Tasks:**
- [ ] `HypothesisTournament` — bracket-style elimination between competing hypotheses
- [ ] Temporal reasoning layer — time-aware hypothesis evolution (when did evidence arrive?)
- [ ] Multi-round structured debate with role-based adversarial agents
- [ ] `EvidenceWeightManager` — dynamic evidence confidence scoring
- [ ] Retrospective analysis — system analyzes its own past reasoning for bias patterns
- [ ] `SyntheticPeerReview` — hypothesis evaluated against generated counter-hypotheses
- [ ] Confidence calibration via historical prediction accuracy
- [ ] Tests for all new reasoning components

**Success Criteria:**
- Hypothesis quality scores improve by ≥ 10% vs. Phase 9 baseline
- Tournament produces clearly superior hypothesis in ≥ 85% of benchmark cases

---

### Phase 12 — Scientific Autonomy

**Goal:** Long-running autonomous research campaigns with citation tracking and external source integration.

**Planned Tasks:**
- [ ] `ResearchCampaign` — multi-session research goal spanning days or weeks
- [ ] Persistent agent identities across sessions (agent remembers prior interactions)
- [ ] External source integration (arXiv API, PubMed, web search for evidence)
- [ ] Citation graph: track which external sources inform which hypotheses
- [ ] Automatic evidence freshness expiry (evidence older than N days downweighted)
- [ ] `ResearchReport` generator — structured PDF/MD output of campaign findings
- [ ] Long-horizon goal decomposition: decompose 6-month research goal into weekly agenda
- [ ] Evaluation harness for scientific claim accuracy vs. ground truth
- [ ] Tests for campaign management and citation tracking

**Success Criteria:**
- System autonomously runs 24h research campaign with zero human intervention
- Campaign produces structured report with citations
- All findings traceable from source through reasoning chain to conclusion

---

## Current Backlog (Immediate)

These tasks are identified but not yet scheduled to a phase:

### High Priority
- [ ] Load testing: benchmark coordination endpoint under concurrent requests
- [ ] Structured logging: add correlation_id to all log lines for request tracing
- [ ] API rate limit: expose current limit and usage via response headers
- [ ] Session cleanup job: prune expired sessions from PostgreSQL periodically
- [ ] Qdrant collection backup: periodic snapshot of research_hypotheses collection

### Medium Priority
- [ ] Admin dashboard: tenant management UI
- [ ] API key rotation: support TTL-based key expiry
- [ ] Evidence citation format: standardize evidence[] as structured citation objects
- [ ] Hypothesis deduplication: detect near-duplicate entries before storing to Qdrant
- [ ] ReasoningTrace export: CSV/JSON export endpoint for audit purposes

### Low Priority
- [ ] Multi-language support: hypothesis generation in languages other than English
- [ ] Cost tracking: estimated token costs per workflow run
- [ ] Webhook support: POST to external URL on workflow completion
- [ ] CLI tool: `irds run --goal "..." --workflow` for terminal usage

---

## Development Conventions for New Tasks

Before marking any task complete:

1. **Tests written and passing** — no new functionality without tests
2. **Lint clean** — `ruff check .` must return 0 errors
3. **Docs updated** — if subsystem is new: update `ROADMAP.md`, `ARCHITECTURE.md`, `PROJECT_STATUS.md`
4. **Heuristic mode works** — every new component must operate without external services
5. **Governance wired** — any new agent action must flow through PolicyEnforcer
6. **Observability present** — Prometheus metric or OTel span for any new critical path
7. **No circular imports** — verify with `python -c "import src.api.main"` with no ImportError
