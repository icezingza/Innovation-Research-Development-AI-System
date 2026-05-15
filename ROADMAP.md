# Roadmap

Strategic direction: Distributed Cognitive Infrastructure → Persistent Semantic Runtime → Autonomous Scientific Intelligence Platform

## Completed

### Phase 1 — Core Runtime Foundation
- Provider-agnostic inference layer (OpenAI, Ollama, fallback chain)
- Memory stack: Qdrant, Neo4j, Redis, PostgreSQL connectors
- BaseAgent lifecycle (perceive → reason → act) with OTel tracing
- ResearchAgent with hypothesis evolution and semantic memory
- CognitivePipeline with PolicyEnforcer governance
- FastAPI application with health, metrics, research task endpoints
- ReasoningTrace (three-tier: memory + Redis + PostgreSQL)

### Phase 2 — Knowledge Infrastructure
- KnowledgeGraph (Neo4j Cypher: hypothesis lineage, contradictions)
- ResearchWorkflow (autonomous: plan → parallel research → debate → recursive → synthesis)
- AsyncScheduler (priority queue, cancellable tasks)
- GovernanceAuditLog (append-only, Redis persistence)
- WorkflowRecord (persistent workflow execution state)
- API: POST/GET /research/workflows, GET /governance/audit

### Phase 3 — Multi-Agent Coordination
- RuntimeEventBus (async pub/sub, wildcard topics, isolated handlers)
- HypothesisAgent, CritiqueAgent, SynthesisAgent (specialized cognitive agents)
- AgentCoordinator (parallel hypothesis → critique → synthesis pipeline)
- API: POST /cognition/coordinate, GET /cognition/events/stats

### Phase 4 — Persistent Semantic Runtime
- ResearchMemory (cross-session knowledge: in-memory + PostgreSQL + Qdrant)
- HypothesisRecord (persistent hypothesis storage across sessions)
- MemoryAgent (reactive subscriber: persists synthesis + high-confidence hypotheses)
- ReactiveSubscriber ABC (infrastructure agents distinct from cognitive agents)
- API: GET /intelligence/report, /intelligence/recall, /intelligence/hypotheses

### Phase 5 — Security + Production Hardening
- APIKeyManager (X-API-Key header auth, constant-time comparison)
- RateLimiter (sliding-window per client, in-memory)
- SecurityMiddleware (reads from app.state, exempt paths for health/metrics)
- AsyncWorkerPool (bounded concurrency pool draining AsyncScheduler)
- StreamManager + SSE streaming (GET /streams/workflows/{id})
- QualityTracker (reasoning performance trends, auto-tuning recommendations)
- Context continuity wired into ResearchWorkflow and AgentCoordinator
- .env.example, docker-compose with volumes + Prometheus
- ARCHITECTURE.md

### Phase 6 — Distributed Execution
- RedisEventBus (Redis Streams XADD/XREADGROUP for multi-process delivery)
- create_event_bus() factory (hybrid: Redis when available, in-memory fallback)
- Consumer group isolation per process; local handlers still fire in same process
- Alembic migration setup (alembic.ini, env.py, versions/001_initial_schema)

### Phase 7 — Adaptive Cognition (Self-Improvement)
- AdaptiveConfigManager: reads QualityTracker trends, auto-tunes RecursiveConfig + WorkflowConfig
- Conservative adjustments (±1 depth per cycle, bounded [2, 8])
- ConfigSnapshot history; wired into lifespan

### Phase 8 — Autonomous Research Agenda
- ResearchAgenda: scans ResearchMemory for low-confidence / sparse topics → AgendaItem list
- Priority scoring (combined sparse+low-confidence = priority 9–10)
- API: GET /intelligence/agenda, POST /intelligence/agenda/run (submits to scheduler)

### Phase 9 — Cognitive Operating System
- CognitiveSessionManager: persistent session state (goals, workflow IDs, findings count)
  Redis-backed with in-memory fallback; TTL 24 h; LRU eviction at 512 sessions
- AgentSpawner: runtime agent creation + scale_coordinator() injection
- API: POST/GET/DELETE /sessions, POST /sessions/{id}/goals

## Remaining (Future)

### Extended Distributed Execution
- Distributed worker pool (workers across multiple processes/hosts via Redis Streams)
- Task routing by agent capability/specialization
- Cross-process cancellation propagation

### Extended Advanced Cognition
- Multi-hypothesis tournament (N agents compete, best survives)
- Temporal reasoning: hypothesis confidence decay over time
- Cross-domain hypothesis transfer (apply findings across research areas)

### Extended Scientific Autonomy
- Long-running research sessions with checkpointing
- Structured literature citation and evidence grounding
- Peer-review simulation (multi-agent critique panels)

### Extended Cognitive Operating System
- Persistent agent identities across restarts
- Inter-session learning: performance improves across sessions
- Pluggable cognition modules (swap reasoning engines)
- Multi-tenant cognitive isolation

## Architecture Invariants

These must never be violated:
- All agent execution is observable (OTel traces + Prometheus metrics)
- All governance decisions are auditable (GovernanceAuditLog)
- All external services are optional (graceful degradation)
- No blocking I/O inside cognition flows
- Secrets via environment variables only
