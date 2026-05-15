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

## Remaining

### Phase 6 — Distributed Execution
- Redis Streams as EventBus backend (replace in-memory for multi-process)
- Distributed worker pool (workers across multiple processes/hosts)
- Task routing by capability/specialization
- Cross-process state consistency via Redis

### Phase 7 — Advanced Cognition
- Self-improvement loop: QualityTracker → auto-tune RecursiveConfig + WorkflowConfig
- Multi-hypothesis tournament (N agents compete, best survives)
- Temporal reasoning: hypothesis confidence decay over time
- Cross-domain hypothesis transfer (apply findings across research areas)

### Phase 8 — Scientific Autonomy
- Autonomous research agenda: system identifies its own research gaps
- Long-running research sessions with checkpointing
- Structured literature citation and evidence grounding
- Peer-review simulation (multi-agent critique panels)

### Phase 9 — Cognitive Operating System
- Agent spawning: coordinator can create new specialized agents at runtime
- Persistent agent identities with long-term memory
- Inter-session learning: performance improves across restarts
- Pluggable cognition modules (swap reasoning engines)
- Multi-tenant cognitive isolation

## Architecture Invariants

These must never be violated:
- All agent execution is observable (OTel traces + Prometheus metrics)
- All governance decisions are auditable (GovernanceAuditLog)
- All external services are optional (graceful degradation)
- No blocking I/O inside cognition flows
- Secrets via environment variables only
