
# 📚 Documentation Handbook (NRE v5.0.0 Sovereign Edition)

Before writing, updating, or testing any codebase features, you MUST read the relevant handbook spec first:
* **Product Goals & Journeys:** Read [docs/prd.md](docs/prd.md)
* **UI/UX & Dashboard Elements:** Read [docs/design.md](docs/design.md)
* **Subsystems & Core Topology:** Read [docs/architecture.md](docs/architecture.md)
* **Agent Specs & Prompt Roles:** Read [docs/agents.md](docs/agents.md)
* **5-Tier Memory & Vector RAG:** Read [docs/memory.md](docs/memory.md)
* **Workflow Tasks & Concurrency:** Read [docs/tasks.md](docs/tasks.md)
* **Sovereign Rules & Security:** Read [docs/rules.md](docs/rules.md)
* **Skill System & Context7 CLI:** Read [docs/skills.md](docs/skills.md)

---

# Project Overview

Innovation-Research-Development-AI-System is a long-term cognitive infrastructure project focused on building:

- distributed cognitive runtimes
- autonomous research orchestration
- persistent semantic reasoning
- multi-agent scientific intelligence
- adaptive memory systems

This is NOT a chatbot project.

The system is designed as a persistent cognitive operating infrastructure capable of:
- orchestrating research agents
- maintaining long-term semantic memory
- evolving reasoning structures
- coordinating distributed cognition
- supporting autonomous scientific workflows

**Current status: Phases 1–9 implemented. System is functional end-to-end in heuristic mode (no external services required).**

Primary optimization goals:
- scalability
- modular cognition
- reasoning traceability
- persistent memory
- runtime observability
- long-term maintainability

Avoid:
- shallow abstractions
- unnecessary framework complexity
- disconnected experimental modules
- monolithic architecture
- hype-driven implementations

Prefer:
- composable systems
- observable runtimes
- explicit reasoning flows
- modular infrastructure
- production-oriented architecture


# Tech Stack

Core Stack:
- Python 3.12+
- FastAPI
- Pydantic v2
- AsyncIO
- Docker
- Docker Compose
- Alembic (database migrations)

Memory Infrastructure:
- Qdrant (vector memory)
- Neo4j (knowledge graph)
- PostgreSQL (structured persistence)
- Redis (runtime synchronization + session state + event streams)

AI / Cognition:
- OpenAI-compatible inference APIs
- Sentence Transformers
- LangChain only when necessary
- Custom orchestration layers preferred

Observability:
- Prometheus
- OpenTelemetry
- Structured logging

Testing:
- pytest
- pytest-asyncio

Do NOT introduce:
- Django
- Flask
- TensorFlow monoliths
- unnecessary frontend frameworks
- tightly coupled architectures
- hidden magic abstractions

Avoid:
- synchronous runtime patterns
- global mutable state
- blocking I/O inside cognition flows


# Architecture

Core Architecture:

```
src/
├── agents/              → cognitive agents (BaseAgent, HypothesisAgent, CritiqueAgent,
│                           SynthesisAgent, ResearchAgent, MemoryAgent)
├── runtime/             → execution runtime and scheduling
│                           (AsyncScheduler, AsyncWorkerPool, StreamManager,
│                            RuntimeStateManager, CognitiveSessionManager, AgentSpawner)
├── memory/              → persistent cognition layers
│                           (ResearchMemory, ContextEngine, KnowledgeGraph,
│                            Qdrant/Neo4j/Redis/PostgreSQL connectors)
├── reasoning/           → reasoning trace systems
│                           (ReasoningTrace, RecursiveReasoningLoop, ReflectionEngine,
│                            ContradictionAnalyzer, QualityTracker, AdaptiveConfigManager)
├── orchestration/       → distributed coordination
│                           (AgentCoordinator, ResearchWorkflow, CognitivePipeline,
│                            DebateRuntime, ResearchAgenda)
├── infrastructure/      → event systems and runtime infrastructure
│                           (RuntimeEventBus, RedisEventBus, ReactiveSubscriber)
├── governance/          → policy enforcement and safety
│                           (PolicyEnforcer, GovernanceAuditLog)
├── telemetry/           → metrics and observability
│                           (Prometheus metrics, OpenTelemetry tracing)
├── protocols/           → inter-agent communication contracts
├── inference/           → LLM provider abstraction
│                           (InferenceRouter, OpenAIProvider, OllamaProvider,
│                            EmbeddingProvider)
├── security/            → API authentication and rate limiting
│                           (APIKeyManager, RateLimiter)
├── api/                 → FastAPI endpoints + middleware + lifespan
└── experiments/         → isolated research prototypes
```

Rules:
- Runtime logic belongs in runtime/
- Persistent memory logic belongs in memory/
- Agent coordination belongs in orchestration/
- Shared runtime infrastructure belongs in infrastructure/
- Safety and validation belong in governance/
- Reasoning lineage belongs in reasoning/
- Inference abstraction belongs in inference/

Do not:
- mix orchestration with memory logic
- place business logic inside API routes
- create giant multi-purpose classes
- create hidden dependencies between modules

Prefer:
- composable services
- async-first architecture
- explicit interfaces
- isolated cognition modules

New subsystem?
Create:
src/{domain}/

before introducing cross-domain coupling.


# Implemented Subsystems (reference)

## Event Bus
- `RuntimeEventBus` — in-memory async pub/sub, wildcard topics (`hypothesis.*`, `*`)
- `RedisEventBus` — extends RuntimeEventBus with Redis Streams (XADD/XREADGROUP)
- `create_event_bus(redis_client)` — factory: Redis when available, in-memory fallback
- Topics: `hypothesis.generated`, `hypothesis.critiqued`, `synthesis.ready`, `coordination.*`

## Agent Pipeline
- `HypothesisAgent` → `CritiqueAgent` → `SynthesisAgent` (parallel phases via AgentCoordinator)
- `MemoryAgent` — ReactiveSubscriber, persists high-quality findings via EventBus
- `AgentSpawner` — runtime agent creation, `scale_coordinator()` injection

## Memory
- `ResearchMemory` — 3-tier: in-memory ring buffer → PostgreSQL (HypothesisRecord) → Qdrant
- `ContextEngine` — semantic search via Qdrant + embeddings
- `KnowledgeGraph` — Neo4j hypothesis lineage + contradiction tracking

## Reasoning
- `RecursiveReasoningLoop` — iterative hypothesis evolution until convergence
- `QualityTracker` — trend analysis (improving / stable / declining) from ReasoningTrace
- `AdaptiveConfigManager` — auto-tunes RecursiveConfig + WorkflowConfig from QualityTracker

## Orchestration
- `ResearchWorkflow` — plan → parallel research → debate → recursive refinement → synthesis
- `AgentCoordinator` — parallel hypothesis generation + critique + synthesis with context recall
- `ResearchAgenda` — scans ResearchMemory for gaps, generates AgendaItems by priority

## Sessions
- `CognitiveSessionManager` — Redis-backed sessions (24 h TTL), in-memory LRU fallback
- Tracks: goals, workflow IDs, findings count, metadata

## Security
- `APIKeyManager` — X-API-Key header, constant-time comparison, dev mode when empty
- `RateLimiter` — sliding-window per client (60 req/min default)
- `SecurityMiddleware` — reads from app.state, exempt: /health, /metrics

## Database
- Alembic migrations at `alembic/`
- Tables: `research_tasks`, `workflow_records`, `hypothesis_records`, `reasoning_traces`


# Coding Conventions

General Rules:
- Python type hints required everywhere
- Avoid `Any` unless justified
- Async-first design
- Prefer composition over inheritance
- Small focused classes
- Explicit dependencies only

Naming:
- snake_case for functions and files
- PascalCase for classes
- descriptive variable names only

Avoid:
- abbreviations
- dead code
- commented-out code blocks
- speculative abstractions
- premature optimization

Limits:
- files ideally under 400 lines
- functions ideally under 50 lines
- classes should have single responsibility

Error Handling:
- never silently swallow exceptions
- raise domain-specific errors when possible
- structured logging only

Comments:
- explain WHY
- do not explain obvious syntax


# Cognitive System Principles

The project must evolve toward:
- persistent cognition
- recursive reasoning
- semantic continuity
- distributed coordination
- autonomous research workflows

The project must NOT drift into:
- generic chatbot frameworks
- prompt-engineering-only systems
- demo-only architectures
- hype abstractions without runtime value

Every major subsystem should improve at least one:
- reasoning persistence
- orchestration scalability
- memory consistency
- runtime observability
- governance enforcement
- adaptive cognition


# Memory Architecture

Memory Layers:
- Vector Memory → Qdrant (semantic search via ContextEngine)
- Graph Memory → Neo4j (hypothesis lineage, contradictions via KnowledgeGraph)
- Runtime State → Redis (ReasoningTrace TTL, GovernanceAuditLog, session state, event streams)
- Structured Persistence → PostgreSQL (ResearchTask, WorkflowRecord, HypothesisRecord, ReasoningTraceRecord)
- Cross-session → ResearchMemory (3-tier: ring buffer → PostgreSQL → Qdrant)

Rules:
- cognition should be replayable
- reasoning should be traceable
- semantic state should persist across cycles

Do not:
- store cognition only in RAM
- tightly couple memory providers
- mix runtime cache with long-term memory


# Runtime & Orchestration

Runtime goals:
- distributed execution
- adaptive scheduling
- event-driven cognition
- multi-agent coordination

All runtime systems should support:
- async execution
- cancellation safety
- telemetry hooks
- observability

Avoid:
- blocking operations
- hidden runtime mutations
- recursive runaway execution

Schedulers must:
- support prioritization (TaskPriority 1=CRITICAL … 10=BACKGROUND)
- support future distributed scaling
- avoid starvation conditions

EventBus rules:
- producers never reference MemoryAgent or other subscribers directly
- subscribers register via `ReactiveSubscriber.register(bus)`
- wildcard subscriptions use `topic.*` or `*` pattern


# Governance & Safety

Governance is mandatory infrastructure.

All cognition flows should eventually support:
- runtime validation
- reasoning trace inspection
- execution policy enforcement
- safety boundaries
- auditability

Do not:
- bypass governance layers
- disable validation silently
- introduce unrestricted autonomous execution


# Observability

Every critical runtime component should expose:
- metrics
- logs
- execution traces

Telemetry priorities:
- reasoning latency
- event throughput
- agent coordination health
- memory synchronization state
- runtime stability

Prefer:
- structured logs
- traceable execution flows
- measurable cognition


# Testing & Quality

Before marking work complete:
- run tests (`pytest`)
- run linting (`ruff check .`)
- verify async correctness
- validate imports
- verify no circular dependencies

Testing Requirements:
- runtime logic requires tests
- orchestration requires async tests
- memory systems require persistence validation
- governance systems require safety validation

Current coverage: **207 tests, 0 failures, 0 lint errors**

Avoid:
- fake placeholder tests
- snapshot-only testing
- untested orchestration logic


# File Placement Rules

New runtime logic:
→ src/runtime/

New memory systems:
→ src/memory/

New reasoning systems:
→ src/reasoning/

New distributed coordination:
→ src/orchestration/

New infrastructure:
→ src/infrastructure/

New governance layers:
→ src/governance/

New inference providers:
→ src/inference/

New security components:
→ src/security/

Experimental prototypes:
→ src/experiments/

Rules:
- prefer extending existing systems
- avoid near-duplicate abstractions
- create reusable infrastructure carefully
- one-off utilities should stay local


# Commands

Environment Setup:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Development server:
```bash
uvicorn src.api.main:app --reload
```

Database migrations:
```bash
alembic upgrade head        # apply all migrations
alembic revision --autogenerate -m "description"  # generate new migration
```

Tests:
```bash
pytest                      # full suite
pytest -s                   # with stdout (async)
pytest tests/test_foo.py    # single file
```

Lint & Format:
```bash
ruff check .                # lint
ruff format .               # format
```

Docker (full stack: postgres, redis, qdrant, neo4j, prometheus, api):
```bash
cp .env.example .env
docker compose up --build
```

Infrastructure (already in docker-compose.yml):
- PostgreSQL :5432
- Redis :6379
- Qdrant :6333
- Neo4j :7474 / :7687
- Prometheus :9090
- API :8000


# Security Rules

Never:
- commit secrets
- commit .env files
- hardcode API keys
- expose internal runtime endpoints publicly
- log sensitive runtime state

All secrets:
- environment variables only (see .env.example)

All external model access:
- configurable providers only (OPENAI_API_KEY, OLLAMA_BASE_URL)

Governance rules must NOT be bypassed silently.

Agent autonomy should always:
- remain observable
- remain interruptible
- remain auditable


# Strategic Direction

This project is evolving toward:

Distributed Cognitive Infrastructure
→ Persistent Semantic Runtime
→ Autonomous Scientific Intelligence Platform
→ Cognitive Operating System ← **current position**

Long-term priorities:
1. persistent memory
2. distributed orchestration
3. reasoning traceability
4. governance enforcement
5. adaptive cognition
6. runtime observability
7. scientific autonomy

Do not lose architectural direction.

Every implementation should strengthen:
- cognition persistence
- orchestration capability
- reasoning quality
- infrastructure scalability
- governance integrity
- operational stability


# Documentation Rules

When adding major systems:
- update ROADMAP.md
- update ARCHITECTURE.md
- update PROJECT_STATUS.md

When architecture changes:
- document rationale
- explain tradeoffs
- explain scalability implications

Avoid undocumented architectural drift.


# Final Philosophy

This repository is not a collection of scripts.

It is an evolving cognitive infrastructure system.

Optimize for:
- longevity
- composability
- observability
- persistence
- scalability
- reasoning integrity

Prefer systems that can evolve for years.
Avoid short-term hacks that damage architecture.
