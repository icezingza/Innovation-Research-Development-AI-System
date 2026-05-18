# 👥 Cognitive Agent Specifications — NamoNexus

## 🚀 1. Core Agent Personas & Protocols

Every agent in NamoNexus inherits from `BaseAgent` and communicates strictly through domain events via the `EventBus`. The system defines specific, highly specialized roles to avoid conflicts and maintain precise reasoning paths.

```
                  ┌────────────────────────┐
                  │      AgentSpawner      │
                  └───────────┬────────────┘
                              │ instantiates
                              ▼
┌────────────────────────────────────────────────────────────┐
│                    AgentCoordinator                        │
│                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐  │
│  │ HypothesisAgent  │  │  CritiqueAgent   │  │Synthesis│  │
│  │ (Propose)        │  │  (Refute)        │  │Agent     │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────▲─────┘  │
└───────────┼─────────────────────┼─────────────────┼────────┘
            │ hypothesis.generated│ hypothesis.critiqued
            ▼                     ▼                 │
      ┌─────────────────────────────────┐           │
      │       Runtime Event Bus         ├───────────┘
      └────────────────┬────────────────┘
                       │ reactive dispatch
                       ▼
             ┌──────────────────┐
             │   MemoryAgent    │
             │   (Persist)      │
             └──────────────────┘
```

---

## 🛠️ 2. Agent Catalog & Details

### 2.1. HypothesisAgent (`src/agents/hypothesis_agent.py`)
* **Role:** Proposes initial research statements and iteratively evolves hypotheses.
* **Prompt Contract:**
  * Must ingest the user's objective, recalled prior evidence from vector memory, and active critiques.
  * Must output a clean structured proposal: `statement`, `confidence` score (0.0 to 1.0), and list of supporting `evidence` nodes.
* **Event Actions:**
  * Publishes: `hypothesis.generated` event.

### 2.2. CritiqueAgent (`src/agents/critique_agent.py`)
* **Role:** Stress-tests proposed hypotheses to identify logical fallacies, contradictions, and negative evidence.
* **Prompt Contract:**
  * Acts as a critical peer. Must analyze the hypothesis statement and identify potential bias, circular reasoning, or data contradictions.
  * Must output a detailed critique: `contradictions_detected` list, `weaknesses` list, and `confidence_adjustment` value.
* **Event Actions:**
  * Subscribes to: `hypothesis.generated`.
  * Publishes: `hypothesis.critiqued` event.

### 2.3. SynthesisAgent (`src/agents/synthesis_agent.py`)
* **Role:** Resolves conflicts, merges divergent lines of thinking, and synthesizes the finalized conclusion.
* **Prompt Contract:**
  * Ingests the complete lineage: all generated hypotheses, critiques, and contradiction logs.
  * Must produce a unified outcome: `synthesis_statement`, `final_confidence` score, and `unresolved_questions` for future research agenda items.
* **Event Actions:**
  * Subscribes to: `hypothesis.critiqued`.
  * Publishes: `synthesis.ready` event.

### 2.4. MemoryAgent (`src/agents/memory_agent.py`)
* **Role:** Performs background synchronization and clean-ups.
* **Reactive Nature:** Inherits from `ReactiveSubscriber`. Runs in the background, listening strictly to the event bus.
* **Actions:**
  * On `hypothesis.generated`: Indexes the proposal chunk into Qdrant vector store.
  * On `synthesis.ready`: Stores the finalized results in PostgreSQL, sets cache TTLs in Redis, and pushes nodes to Neo4j.
  * Ensures zero blocking of the core agent execution loops.

### 2.5. ResearchAgent (`src/agents/research_agent.py`)
* **Role:** Performs external search queries and documentation lookups.
* **Actions:**
  * Queries FAISS local storage.
  * Integrates Context7 MCP or other tools to pull live SDK, API, and cloud documentation to solve information gaps.

---

## ⚡ 3. Lifecycle & Agent Spawner

### 3.1. Agent Execution Flow
1. **Perceive:** Receive task payload / event topic details.
2. **Policy Check:** Run payload through `PolicyEnforcer` to guarantee prompt boundaries and safety limits.
3. **Reason:** Submit state parameters to LLM providers (via `InferenceRouter`) to generate response properties.
4. **Act:** Format output as JSON and publish back to `EventBus`.

### 3.2. Dynamic Scaling with `AgentSpawner`
The `AgentSpawner` (`src/runtime/agent_spawner.py`) manages agent instances at runtime:
```python
async def scale_coordinator(
    coordinator: AgentCoordinator,
    agent_type: str,
    count: int = 1
) -> list[BaseAgent]:
    """Dynamically scales up agents and registers them in the active coordinator."""
```
This is critical for high-throughput multi-tenant loads: when a tenant upgrades to the Enterprise tier, the scheduler triggers the spawner to instantiate multiple parallel `HypothesisAgent` instances, reducing coordination latency by up to 60%.
