# Memory System Reference
# Innovation Research & Development AI System (IRDS)

**Version:** 1.0  
**Date:** 2026-05-17

---

## 1. Memory Architecture Overview

IRDS implements a **4-tier persistent memory architecture** where each tier serves a distinct access pattern and durability requirement. All tiers are optional at runtime — the system degrades gracefully when backends are unavailable.

```
┌─────────────────────────────────────────────────────────┐
│                   ResearchMemory Facade                 │
│         (unified write/recall interface for agents)     │
└──────────┬──────────────────────────────────────────────┘
           │
     ┌─────┼──────────────────────────────────┐
     ▼     ▼                ▼                 ▼
┌─────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│  Tier 0     │   │   Tier 1     │   │     Tier 2       │   │   Tier 3     │
│  In-Memory  │   │  PostgreSQL  │   │     Qdrant       │   │    Neo4j     │
│  Ring Buffer│   │  Relational  │   │     Vector       │   │    Graph     │
│  (2000 cap) │   │  Persistence │   │  Semantic Search │   │   Lineage    │
│  Always on  │   │  Permanent   │   │  Embeddings      │   │ Contradictions│
└─────────────┘   └──────────────┘   └──────────────────┘   └──────────────┘

+ Redis: runtime state, trace cache, audit log, event streams, sessions
```

---

## 2. Memory Entry Schema

All memory tiers store or index `MemoryEntry` objects:

```python
@dataclass
class MemoryEntry:
    entry_id: str           # UUID, auto-generated
    topic: str              # research domain or question keyword
    statement: str          # hypothesis or finding text
    confidence: float       # 0.0–1.0 quality score
    source: str             # agent_id or "external"
    session_id: str | None  # originating cognitive session
    evidence: list[str]     # supporting evidence strings
    generation: int         # 0 = initial, 1+ = evolved
    created_at: datetime    # wall clock time
```

---

## 3. ResearchMemory

**File:** `src/memory/research_memory.py`  
**Purpose:** Unified cross-session knowledge accumulation facade. Used by all agents and orchestrators.

### Write Path

```python
await research_memory.store(entry: MemoryEntry)

Execution:
  1. _buffer.append(entry)             ← always (ring buffer, max 2000)
  2. _store_postgres(entry)            ← if session_factory configured
       INSERT INTO hypothesis_records (...)
  3. _store_qdrant(entry)              ← if context_engine configured
       embed(entry.statement) → vector
       qdrant.upsert(collection="research_hypotheses", ...)
```

### Read Path

```python
entries = await research_memory.recall(topic: str, limit: int = 5) -> list[MemoryEntry]

Execution:
  1. If ContextEngine available:
       packet = await context_engine.build(topic)
       → [MemoryEntry, ...] from Qdrant semantic search
  2. Fallback (no Qdrant):
       keyword_overlap(topic, _buffer) → sorted by overlap score → top N
```

### Statistics

```python
stats = await research_memory.stats() -> dict

Returns:
  {
    "total_entries": 142,
    "avg_confidence": 0.74,
    "sources": {"hypothesis_agent": 89, "synthesis_agent": 53},
    "backends_available": {
      "in_memory": True,
      "postgres": True,
      "qdrant": True
    }
  }
```

---

## 4. ContextEngine

**File:** `src/memory/context_engine.py`  
**Purpose:** Builds semantic context packets for agent perception using Qdrant vector search.

```python
packet = await context_engine.build(topic: str, limit: int = 5) -> ContextPacket

Execution:
  1. EmbeddingProvider.embed(topic) → 384-dim vector
  2. QdrantClient.search(
       collection="research_hypotheses",
       query_vector=vector,
       limit=limit,
       score_threshold=0.5
     )
  3. Map search results → [MemoryEntry, ...]
  4. Compute continuity_score = mean(search_scores)

@dataclass
class ContextPacket:
    topic: str
    entries: list[MemoryEntry]   # semantically similar past findings
    continuity_score: float      # 0.0–1.0 semantic similarity
    retrieved_at: datetime
```

The `continuity_score` indicates how strongly the current topic connects to past research. Agents use this to calibrate confidence in recall.

---

## 5. KnowledgeGraph

**File:** `src/memory/knowledge_graph.py`  
**Purpose:** Tracks hypothesis lineage and contradiction relationships in Neo4j.

### Node Schema
```cypher
(h:Hypothesis {
  id: "uuid",
  statement: "...",
  confidence: 0.78,
  generation: 1,
  topic: "superconductivity",
  session_id: "sess_abc",
  created_at: datetime()
})
```

### Edge Schema
```cypher
// Hypothesis evolved from prior
(h2)-[:EVOLVED_FROM]->(h1)

// Contradiction detected
(h1)-[:CONTRADICTS]->(h2)

// Topic grouping
(h1)-[:ABOUT]->(t:Topic {name: "superconductivity"})
```

### Key Methods
```python
await knowledge_graph.store_hypothesis(hypothesis: dict) -> str
    # Creates Hypothesis node, links EVOLVED_FROM if generation > 0

await knowledge_graph.store_contradiction(h1_id: str, h2_id: str) -> None
    # Creates CONTRADICTS edge between two hypothesis nodes

lineage = await knowledge_graph.get_lineage(hypothesis_id: str) -> list[dict]
    # Returns chain of EVOLVED_FROM nodes back to generation 0

contradictions = await knowledge_graph.get_contradictions(topic: str) -> list[dict]
    # Returns all CONTRADICTS edges for topic
```

---

## 6. MemoryManager

**File:** `src/memory/memory_manager.py`  
**Purpose:** Unified health check and routing coordinator for all memory backends.

```python
health = await memory_manager.healthcheck() -> dict

Returns:
  {
    "vector": {
      "backend": "qdrant",
      "status": "healthy",
      "latency_ms": 12
    },
    "graph": {
      "backend": "neo4j",
      "status": "healthy",
      "latency_ms": 8
    },
    "runtime": {
      "backend": "redis",
      "status": "healthy",
      "latency_ms": 2
    },
    "persistence": {
      "backend": "postgresql",
      "status": "healthy",
      "latency_ms": 5
    }
  }
```

---

## 7. Backend Connectors

### 7.1 PostgreSQL Store

**File:** `src/memory/postgres_store.py`

```python
class PostgresMemoryStore:
    # asyncpg connection pool
    # Tables: hypothesis_records, reasoning_traces, workflow_records, research_tasks

    async def store_hypothesis(self, entry: MemoryEntry) -> str: ...
    async def get_hypotheses(self, topic: str, limit: int) -> list[dict]: ...
    async def store_trace(self, trace_entry: TraceEntry) -> None: ...
    async def get_traces(self, limit: int) -> list[dict]: ...
```

**Connection:** `POSTGRES_URL=postgresql+asyncpg://user:pass@host:5432/dbname`

### 7.2 Qdrant Connector

**File:** `src/memory/qdrant_connector.py`

```python
class QdrantMemoryConnector:
    collection: str = "research_hypotheses"
    vector_size: int = 384  # all-MiniLM-L6-v2 output dimensions
    distance: Distance = Distance.COSINE

    async def upsert(self, entry_id: str, vector: list[float], payload: dict) -> None: ...
    async def search(self, vector: list[float], limit: int, score_threshold: float) -> list[ScoredPoint]: ...
    async def healthcheck(self) -> bool: ...
    async def ensure_collection(self) -> None: ...  # creates collection if not exists
```

**Connection:** `QDRANT_HOST=localhost`, `QDRANT_PORT=6333`

### 7.3 Neo4j Connector

**File:** `src/memory/neo4j_connector.py`

```python
class Neo4jKnowledgeConnector:
    # Async Neo4j driver
    async def run_query(self, cypher: str, params: dict) -> list[Record]: ...
    async def healthcheck(self) -> bool: ...
    async def close(self) -> None: ...
```

**Connection:** `NEO4J_URI=bolt://localhost:7687`, `NEO4J_USER=neo4j`, `NEO4J_PASSWORD=...`

### 7.4 Redis Store

**File:** `src/memory/redis_store.py`

```python
class RedisRuntimeStore:
    # Used for: sessions, reasoning trace cache, audit log, agent state

    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def append_list(self, key: str, value: str, max_len: int | None) -> None: ...
    async def get_list(self, key: str, limit: int) -> list[str]: ...
```

**Key Namespacing:**
```
irds:session:{session_id}          ← CognitiveSessionManager
irds:trace:{trace_id}              ← ReasoningTrace
irds:audit:{entry_id}              ← GovernanceAuditLog
irds:events:{topic}                ← RedisEventBus streams
```

**Connection:** `REDIS_URL=redis://localhost:6379/0`

---

## 8. ReasoningTrace

**File:** `src/reasoning/reasoning_trace.py`  
**Purpose:** 3-tier trace of all cognitive operations — always available, persistently auditable.

### Tier Architecture

```
Tier A: In-memory ring buffer (always)
  → deque(maxlen=500) of TraceEntry objects
  → immediate availability, no I/O

Tier B: Redis (24h TTL)
  → JSON-serialized to irds:trace:{trace_id}
  → available across processes if Redis connected

Tier C: PostgreSQL (permanent)
  → INSERT INTO reasoning_traces (...)
  → available for long-term audit if PostgreSQL connected
```

### TraceEntry Schema

```python
@dataclass
class TraceEntry:
    trace_id: str           # UUID
    operation: str          # "hypothesis_agent.run", "reflection_engine.analyze", etc.
    input_hash: str         # sha256 of input context
    output_summary: str     # short human-readable summary
    agent_id: str | None    # which agent produced this
    duration_seconds: float
    quality_score: float | None
    timestamp: datetime
```

### Usage

```python
# Record from any component
await reasoning_trace.record(TraceEntry(
    operation="inference_router.complete",
    input_hash=hash(prompt),
    output_summary=f"inference via {provider}, tier={tier}, success={bool(response)}",
    agent_id=agent_id,
    duration_seconds=elapsed
))

# Read recent (for QualityTracker)
entries = reasoning_trace.get_recent(limit=20)  # from in-memory buffer
```

---

## 9. CognitiveSessionManager

**File:** `src/runtime/session_manager.py`  
**Purpose:** Maintains cognitive session state across API calls, with Redis backend and LRU fallback.

### SessionState Schema

```python
@dataclass
class SessionState:
    session_id: str
    created_at: datetime
    updated_at: datetime
    goals: list[str]         # research goals registered in this session
    workflow_ids: list[str]  # workflow IDs run within this session
    findings_count: int      # total MemoryEntry records accumulated
    status: str              # "active" | "closed"
    metadata: dict           # arbitrary context (user_id, tenant_id, etc.)
```

### Storage Strategy

```
Primary:   Redis (irds:session:{session_id}, 24h TTL)
Fallback:  In-memory LRU cache (max 100 sessions)
```

### Key Methods

```python
session = await manager.create(metadata: dict = {}) -> SessionState
state   = await manager.get(session_id: str) -> SessionState | None
await manager.update(session: SessionState) -> None
await manager.add_goal(session_id, goal: str) -> bool
await manager.record_workflow(session_id, workflow_id: str) -> bool
await manager.increment_findings(session_id, count: int = 1) -> bool
await manager.close(session_id: str) -> bool
await manager.delete(session_id: str) -> bool
```

---

## 10. Memory Lifecycle in a Research Workflow

```
ResearchWorkflow.run(goal)
    │
    ├─ 1. recall(goal) → prior_context
    │       ResearchMemory.recall(goal)
    │         → ContextEngine.build(goal) if Qdrant available
    │         → ring buffer keyword fallback otherwise
    │
    ├─ 2. [Agent execution — generates hypotheses]
    │       HypothesisAgent publishes "hypothesis.generated"
    │           → MemoryAgent.handle_event()
    │               → ResearchMemory.store(entry)
    │                   → ring buffer ← always
    │                   → PostgreSQL   ← if available
    │                   → Qdrant       ← if available (via embedding)
    │
    ├─ 3. [Synthesis — synthesizes conclusion]
    │       SynthesisAgent publishes "synthesis.ready"
    │           → MemoryAgent.handle_event()
    │               → ResearchMemory.store(synthesis_entry)
    │
    └─ 4. [Knowledge graph update]
            KnowledgeGraph.store_hypothesis(primary_hypothesis)
              → Creates Hypothesis node in Neo4j
              → Creates EVOLVED_FROM edges if generation > 0
```

---

## 11. GovernanceAuditLog

**File:** `src/governance/audit_log.py`  
**Purpose:** Append-only policy decision log — every PolicyEnforcer decision is recorded.

```python
@dataclass
class AuditEntry:
    entry_id: str
    decision: str           # "ALLOW" | "DENY" | "WARN"
    reason: str
    message_id: str
    sender_id: str
    message_type: str
    content_size_bytes: int
    timestamp: datetime

# Appended to:
# 1. In-memory list (always)
# 2. Redis list (irds:audit:log, max 10000 entries, if Redis available)
```

---

## 12. EmbeddingProvider

**File:** `src/inference/embedding_provider.py`  
**Purpose:** Generates vector embeddings for semantic memory storage and retrieval.

```python
class EmbeddingProvider:
    # Local: SentenceTransformer("all-MiniLM-L6-v2") — always available
    # Remote: OpenAI text-embedding-3-small — if OPENAI_API_KEY set

    async def embed(self, text: str) -> list[float]:
        # Returns 384-dim vector (local) or 1536-dim (OpenAI)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Batch embedding for bulk storage operations
```

Local model is loaded at startup and cached in memory — no API call required after initialization.

---

## 13. Memory Tuning Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Ring buffer capacity | 2000 | Max in-memory entries before FIFO eviction |
| Session TTL | 86400s (24h) | Redis session expiry |
| Trace buffer size | 500 | In-memory trace ring buffer size |
| Trace TTL | 86400s (24h) | Redis trace cache expiry |
| Audit log max | 10000 | Redis audit list max length |
| Qdrant score threshold | 0.5 | Min cosine similarity to include in recall |
| MemoryAgent min confidence | 0.5 | Min confidence to persist a finding |
| Recall limit (default) | 5 | Max entries per recall call |

---

## 14. Degradation Behavior

| Backend Unavailable | Behavior |
|--------------------|----------|
| Qdrant | `recall()` uses ring buffer keyword scoring; no vector embeddings stored |
| PostgreSQL | Hypothesis records not persisted; ring buffer only |
| Neo4j | Lineage and contradiction graph not updated; no error raised |
| Redis (sessions) | In-memory LRU cache used; sessions lost on process restart |
| Redis (events) | RuntimeEventBus used; events not distributed cross-process |
| Redis (traces) | Traces stored in memory ring buffer only |
| All backends | Full heuristic mode: all memory is in-process only |

The system logs a WARNING at startup for each unavailable backend but continues initializing.
