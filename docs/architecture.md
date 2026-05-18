# 🏗️ Technical Architecture — NamoNexus

## 🌐 1. Cognitive Architecture Layer Overview

NamoNexus operates as a distributed cognitive operating infrastructure. The architecture is structured in modular layers, keeping logic separation absolute.

```
┌─────────────────────────────────────────────────────────┐
│                        API Layer                        │
│  FastAPI · SecurityMiddleware · SSE Streaming · Auth    │
├─────────────────────────────────────────────────────────┤
│                  Orchestration Layer                    │
│  AgentCoordinator · ResearchWorkflow · CognitivePipeline│
│  ResearchAgenda · DebateRuntime                         │
├─────────────────────────────────────────────────────────┤
│                    Agent Layer                          │
│  HypothesisAgent · CritiqueAgent · SynthesisAgent      │
│  ResearchAgent · MemoryAgent (reactive) · Spawner       │
├─────────────────────────────────────────────────────────┤
│                  Reasoning Layer                        │
│  RecursiveReasoningLoop · DebateRuntime                 │
│  ReflectionEngine · ContradictionAnalyzer               │
│  ReasoningTrace · QualityTracker · AdaptiveConfig       │
├─────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                    │
│  RuntimeEventBus · RedisEventBus · ReactiveSubscriber   │
│  AsyncScheduler · AsyncWorkerPool · StreamManager       │
├─────────────────────────────────────────────────────────┤
│                   Memory Layer                          │
│  Qdrant (vector) · Neo4j (graph) · PostgreSQL (persist) │
│  Redis (runtime cache) · ResearchMemory (cross-session) │
├─────────────────────────────────────────────────────────┤
│                  Governance Layer                       │
│  PolicyEnforcer · GovernanceAuditLog                    │
├─────────────────────────────────────────────────────────┤
│                  Telemetry Layer                        │
│  Prometheus metrics · OpenTelemetry traces              │
└─────────────────────────────────────────────────────────┘
```

---

## 📡 2. Key Subsystems

### 2.1. Multi-Agent Coordination
The `AgentCoordinator` utilizes specialized agents in parallel execution cycles:
* **HypothesisAgent:** Synthesizes and proposes hypotheses based on task sub-questions and recalled vector memories.
* **CritiqueAgent:** Proactively criticizes proposed hypotheses, identifying gaps, assumptions, or logical flaws.
* **SynthesisAgent:** Combines hypotheses and critiques into a unified, coherent synthesis conclusion.

### 2.2. Distributed Event Bus (Redis Streams)
* **Local In-Memory (`RuntimeEventBus`):** Purely async pub/sub utilizing `asyncio.Queue` and wildcard topic matching (`hypothesis.*`, `synthesis.ready`, `*`).
* **Distributed Stream (`RedisEventBus`):** Integrates Redis Streams (`XADD` and `XREADGROUP`) to run distributed worker processes. Events are delivered to a shared consumer group (`cognitive_workers`) ensuring exactly-once delivery across cluster nodes.
* **Factory pattern:** `create_event_bus(redis_client)` returns `RedisEventBus` when Redis connection is active, falling back to local `RuntimeEventBus` seamlessly.

### 3.3. Five-Tier Memory Stack
* **Vector Memory (Qdrant):** Handles semantic retrieval and cross-session knowledge continuity via `ContextEngine`.
* **Graph Memory (Neo4j):** Interlinks hypotheses, sub-questions, and contradictions. Shows lineage trees and flags semantic conflicts.
* **Persistent DB (PostgreSQL):** Stores master data (`tenants`, `users`) and workflow tables via SQLAlchemy.
* **Cache & Runtime (Redis):** Session management (CognitiveSessionManager), trace TTL caching, and telemetry metrics buffers.
* **Cross-Session Storage (`ResearchMemory`):** Combines in-memory ring-buffers, PostgreSQL tables, and Qdrant collections.

### 2.4. Recursive Reasoning Loop
* The `RecursiveReasoningLoop` drives evolutionary hypothesis optimization. It loops continuously, modifying hypotheses based on critique inputs until the `QualityTracker` signals convergence or max depth limits are reached.
* `AdaptiveConfigManager` dynamically scales the maximum planning sub-questions and loop depths based on moving quality trends (declining quality decreases depth, increasing quality expands depth limits).

---

## 🛡️ 3. Database Isolation, Tenants & Row-Level Security (RLS)

NamoNexus utilizes a multi-tenant strategy to guarantee enterprise-grade data isolation:
1. **Shared-Database Shared-Schema:** All tenant tables contain a `tenant_id` column.
2. **RLS Migration:** PostgreSQL row-level security is applied via Alembic migrations.
3. **Async Middleware Context:** The `AsyncSession` dependency (`get_db`) executes a tenant session prefix set:
```sql
SET LOCAL app.current_tenant_id = 'tenant-uuid';
```
This forces PostgreSQL to filter all SELECT, UPDATE, and DELETE operations automatically at the database level, preventing any possibility of cross-tenant data leaks.

---

## 📈 4. Scaling, Live Spawning & Telemetry

### 4.1. Live Agent Spawning
The `AgentSpawner` allows dynamic runtime scaling of active agents. If task queues are congested, the system triggers `scale_coordinator()` to inject fresh `HypothesisAgent` or `CritiqueAgent` instances directly into live workflows without requiring process restarts.

### 4.2. Telemetry and Health Gating
* **Prometheus:** Exposes raw cognitive metrics at `/metrics` (e.g. `cognitive_latency_seconds`, `event_throughput_total`, `active_workers_count`, `memory_sync_lag`).
* **OpenTelemetry:** Traces the execution path from the `/cognition/coordinate` request down through each agent queue, providing absolute reasoning trace visualization.
