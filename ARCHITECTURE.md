# Architecture

Cognitive Research Runtime — distributed cognitive infrastructure for autonomous scientific reasoning.

## Layer Overview

```
┌─────────────────────────────────────────────────────────┐
│                        API Layer                        │
│  FastAPI · SecurityMiddleware · SSE Streaming           │
├─────────────────────────────────────────────────────────┤
│                  Orchestration Layer                    │
│  AgentCoordinator · ResearchWorkflow · CognitivePipeline│
├─────────────────────────────────────────────────────────┤
│                    Agent Layer                          │
│  HypothesisAgent · CritiqueAgent · SynthesisAgent      │
│  ResearchAgent · MemoryAgent (reactive)                 │
├─────────────────────────────────────────────────────────┤
│                  Reasoning Layer                        │
│  RecursiveReasoningLoop · DebateRuntime                 │
│  ReflectionEngine · ContradictionAnalyzer               │
│  ReasoningTrace · QualityTracker                        │
├─────────────────────────────────────────────────────────┤
│                 Infrastructure Layer                    │
│  RuntimeEventBus · ReactiveSubscriber                   │
│  AsyncScheduler · AsyncWorkerPool · StreamManager       │
├─────────────────────────────────────────────────────────┤
│                   Memory Layer                          │
│  Qdrant (vector) · Neo4j (graph) · PostgreSQL (persist) │
│  Redis (runtime cache) · ResearchMemory (cross-session) │
│  ContextEngine · KnowledgeGraph                        │
├─────────────────────────────────────────────────────────┤
│                  Governance Layer                       │
│  PolicyEnforcer · GovernanceAuditLog                    │
├─────────────────────────────────────────────────────────┤
│                  Telemetry Layer                        │
│  Prometheus metrics · OpenTelemetry traces              │
└─────────────────────────────────────────────────────────┘
```

## Key Subsystems

### Multi-Agent Coordination
`AgentCoordinator` orchestrates three specialized agents in a research pipeline:
1. **HypothesisAgent** — generates and evolves a hypothesis per sub-question (parallel)
2. **CritiqueAgent** — stress-tests each hypothesis (parallel)
3. **SynthesisAgent** — synthesizes all hypotheses into a coherent conclusion

### Autonomous Research Workflow
`ResearchWorkflow` runs a deeper pipeline: plan → parallel research agents → optional debate → optional recursive refinement → knowledge graph storage → synthesis. Publishes progress to `StreamManager` for SSE clients.

### Runtime Event Bus
`RuntimeEventBus` is an async pub/sub bus with wildcard topic matching. Agents publish domain events (`hypothesis.generated`, `synthesis.ready`, etc.). `MemoryAgent` subscribes reactively and persists high-quality findings to `ResearchMemory` without any coupling to the producing agents.

### Cross-Session Memory
`ResearchMemory` accumulates knowledge across sessions. Three-tier: in-memory ring buffer → PostgreSQL (`HypothesisRecord`) → Qdrant semantic search. Each new workflow recalls prior relevant findings to inject as context, making the system genuinely build on prior research.

### Recursive Reasoning
`RecursiveReasoningLoop` iteratively evolves a hypothesis using `HypothesisEvolutionEngine` until one of three convergence conditions is met: quality threshold reached, no improvement detected, or max depth hit. All iterations are recorded in `ReasoningTrace`.

### Governance
`PolicyEnforcer` evaluates every agent message before it reaches the pipeline. Every decision is recorded in `GovernanceAuditLog` (in-memory + Redis). Security middleware handles API key auth and sliding-window rate limiting.

## Data Flow: Coordination Request

```
POST /cognition/coordinate
        │
        ▼
AgentCoordinator.coordinate(goal)
        │
        ├─── ResearchMemory.recall(goal) ──► inject prior_evidence
        │
        ├─── _plan(goal) ──► sub_questions[0..N]
        │
        ├─── asyncio.gather([HypothesisAgent.run(q) for q in sub_questions])
        │         │
        │         └─► EventBus.publish(hypothesis.generated) ──► MemoryAgent
        │
        ├─── asyncio.gather([CritiqueAgent.run(hyp) for hyp in hypotheses])
        │         │
        │         └─► EventBus.publish(hypothesis.critiqued)
        │
        └─── SynthesisAgent.run(hypotheses + critiques)
                  │
                  └─► EventBus.publish(synthesis.ready) ──► MemoryAgent
                  └─► CoordinatedResult
```

## Directory Structure

```
src/
├── agents/          cognitive agents (perceive/reason/act)
├── api/             FastAPI routes, middleware, lifespan, dependencies
├── config.py        pydantic-settings with .env support
├── governance/      policy enforcement, audit log
├── inference/       provider-agnostic LLM + embedding layer
├── infrastructure/  event bus, reactive subscriber
├── memory/          all persistence: vector, graph, relational, cache
├── orchestration/   pipeline, workflow, coordinator, debate
├── protocols/       agent message contracts
├── reasoning/       trace, reflection, contradiction, recursion, quality
├── research/        hypothesis evolution engine
├── runtime/         scheduler, worker pool, state manager, stream manager
├── security/        API key auth, rate limiter
└── telemetry/       prometheus metrics, otel tracing
```

## External Services

| Service | Role | Required |
|---------|------|----------|
| PostgreSQL | Persistent research tasks, reasoning traces, hypothesis records | No (degrades) |
| Redis | Runtime cache, reasoning trace TTL, audit log | No (degrades) |
| Qdrant | Vector memory for semantic search and context continuity | No (degrades) |
| Neo4j | Hypothesis lineage graph and contradiction tracking | No (degrades) |
| OpenAI/Ollama | LLM inference for hypothesis generation and synthesis | No (heuristic fallback) |

All external services are optional — the system runs fully in heuristic mode without any external dependencies.
