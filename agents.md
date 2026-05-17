# Agents Reference
# Innovation Research & Development AI System (IRDS)

**Version:** 1.0  
**Date:** 2026-05-17

---

## 1. Agent System Overview

The agent layer implements the cognitive workforce of IRDS. Every agent is an independent, single-responsibility cognitive unit that follows the perceive → reason → act lifecycle, communicates through explicit message contracts, and publishes events to the event bus without referencing other agents directly.

Agents are **not chatbots**. They are asynchronous cognitive processors that accept structured context, perform domain-specific reasoning, produce typed outputs, and record their operations to the reasoning trace.

---

## 2. BaseAgent

**File:** `src/agents/base.py`

All agents inherit from `BaseAgent`, which provides:
- Lifecycle orchestration (`run()` calls `perceive()` → `reason()` → `act()`)
- OpenTelemetry span wrapping per cycle
- Prometheus metric emission (agent cycle start/complete counters)
- Governance enforcement gate (via PolicyEnforcer)
- Structured logging with agent_id and session_id correlation

```python
class BaseAgent(ABC):
    agent_id: str
    agent_type: str
    inference_router: InferenceRouter | None
    event_bus: RuntimeEventBus | None
    governance: PolicyEnforcer | None
    reasoning_trace: ReasoningTrace | None

    async def run(self, context: dict) -> AgentMessage:
        # 1. Emit metric: agent_cycle_start
        # 2. Start OTel span: agent.{agent_id}.cycle
        # 3. perceive(context) → perception
        # 4. reason(perception)  → reasoning
        # 5. act(reasoning)      → action
        # 6. Build AgentMessage from action
        # 7. PolicyEnforcer.enforce(message) if configured
        # 8. Emit metric: agent_cycle_complete
        # 9. Return AgentMessage

    @abstractmethod
    async def perceive(self, context: dict) -> dict: ...

    @abstractmethod
    async def reason(self, perception: dict) -> dict: ...

    @abstractmethod
    async def act(self, reasoning: dict) -> dict: ...
```

**Constructor Dependencies (all optional):**
```python
BaseAgent(
    agent_id="agent_001",
    inference_router=InferenceRouter(...),   # None = heuristic mode
    event_bus=RuntimeEventBus(...),          # None = no event publishing
    governance=PolicyEnforcer(...),          # None = no governance gate
    reasoning_trace=ReasoningTrace(...),     # None = no trace recording
    memory=ResearchMemory(...),              # None = no memory recall
    context_engine=ContextEngine(...),       # None = no semantic context
)
```

---

## 3. HypothesisAgent

**File:** `src/agents/hypothesis_agent.py`  
**Purpose:** Generates a scientific hypothesis for a single sub-question.

### Lifecycle

```
perceive(context)
  ├─ Extracts: question, session_id, prior_evidence
  ├─ Calls ResearchMemory.recall(question) for prior findings
  └─ Returns: {question, prior_evidence, semantic_context}

reason(perception)
  ├─ If InferenceRouter available:
  │    prompt = f"Generate hypothesis for: {question}\nPrior: {prior_evidence}"
  │    response = await inference_router.complete(prompt, tier="fast")
  │    → structured hypothesis text
  └─ Heuristic fallback:
       → template-based hypothesis construction from question keywords

act(reasoning)
  ├─ Creates hypothesis dict {statement, confidence, topic, evidence, generation}
  ├─ Publishes RuntimeEvent(topic="hypothesis.generated", payload=hypothesis)
  └─ Returns hypothesis dict
```

### Event Published
```python
RuntimeEvent(
    topic="hypothesis.generated",
    payload={
        "statement": "...",
        "confidence": 0.72,
        "topic": "...",
        "source": "hypothesis_agent",
        "session_id": "...",
        "evidence": [...],
        "generation": 0
    }
)
```

### Output AgentMessage
```python
AgentMessage(
    sender_id="hypothesis_agent_001",
    message_type=MessageType.ACTION,
    content={"hypothesis": {...}, "events_published": 1}
)
```

---

## 4. CritiqueAgent

**File:** `src/agents/critique_agent.py`  
**Purpose:** Stress-tests a hypothesis by identifying weaknesses, contradictions, and missing evidence.

### Lifecycle

```
perceive(context)
  ├─ Extracts: hypothesis (AgentMessage or dict), question, session_id
  └─ Returns: {hypothesis_statement, confidence, topic}

reason(perception)
  ├─ If InferenceRouter available:
  │    prompt = f"Critically evaluate: {hypothesis_statement}\nIdentify: weaknesses, contradictions, missing evidence"
  │    response = await inference_router.complete(prompt, tier="fast")
  └─ Heuristic: structured critique template with generic gap analysis

act(reasoning)
  ├─ Produces critique dict {weaknesses, contradictions, confidence_adjustment, critique_summary}
  ├─ Publishes RuntimeEvent(topic="hypothesis.critiqued", payload=critique)
  └─ Returns critique dict
```

### Event Published
```python
RuntimeEvent(
    topic="hypothesis.critiqued",
    payload={
        "original_statement": "...",
        "weaknesses": ["...", "..."],
        "contradictions": ["..."],
        "confidence_adjustment": -0.05,
        "critique_summary": "...",
        "source": "critique_agent"
    }
)
```

---

## 5. SynthesisAgent

**File:** `src/agents/synthesis_agent.py`  
**Purpose:** Synthesizes multiple hypotheses and their critiques into a coherent research conclusion.

### Lifecycle

```
perceive(context)
  ├─ Extracts: hypotheses[], critiques[], goal, session_id
  └─ Returns: {goal, hypothesis_count, hypothesis_statements[], critique_summaries[]}

reason(perception)
  ├─ Calls ReflectionEngine.analyze(statement) for each hypothesis
  │    → quality_score per hypothesis
  ├─ Ranks hypotheses by quality_score
  ├─ Selects primary hypothesis (highest score)
  └─ If InferenceRouter available:
       prompt = f"Synthesize: {goal}\nHypotheses: {ranked_statements}"
       response = await inference_router.complete(prompt, tier="deep")

act(reasoning)
  ├─ Produces synthesis dict {conclusion, primary_hypothesis, quality_score, synthesis_method}
  ├─ Publishes RuntimeEvent(topic="synthesis.ready", payload=synthesis)
  └─ Returns synthesis dict
```

### Event Published
```python
RuntimeEvent(
    topic="synthesis.ready",
    payload={
        "conclusion": "...",
        "primary_hypothesis": "...",
        "quality_score": 0.84,
        "synthesis_method": "reflection_ranked",
        "hypothesis_count": 4,
        "source": "synthesis_agent"
    }
)
```

---

## 6. ResearchAgent

**File:** `src/agents/research_agent.py`  
**Purpose:** Full cognitive lifecycle agent for a single sub-question — generates, evolves, reflects, and returns a research result.

This is the most complex agent. It is used by `CognitivePipeline` for full workflow sub-questions.

### Lifecycle

```
perceive(context)
  ├─ Extracts: question, session_id, prior_context
  ├─ Calls ContextEngine.build(question) → ContextPacket (semantic context from Qdrant)
  └─ Returns: {question, semantic_context, continuity_score, prior_findings}

reason(perception)
  ├─ Phase 1: Initial Hypothesis Generation
  │    InferenceRouter.complete(prompt, tier="fast") OR heuristic
  │    → initial_hypothesis: {statement, confidence, evidence}
  │
  ├─ Phase 2: Hypothesis Evolution (HypothesisEvolutionEngine)
  │    ReflectionEngine.analyze(statement) → gaps, suggestions
  │    HypothesisEvolutionEngine.evolve(hypothesis, gaps) → evolved_hypothesis
  │    → increments generation counter, qualifies statement with conditions
  │
  ├─ Phase 3: Reflection & Quality
  │    ReflectionEngine.analyze(evolved_statement) → quality_score
  │    → quality_score: 0.0–1.0
  │
  └─ Phase 4: Contradiction Detection (if prior_findings exist)
       ContradictionAnalyzer.analyze([evolved_statement, *prior_findings])
       → contradictions: bool, contradiction_details: list

act(reasoning)
  ├─ Builds SubQuestionResult {question, hypothesis, quality_score, generation, contradictions, context_used}
  ├─ Publishes hypothesis.generated event
  └─ Returns SubQuestionResult as dict
```

### Output Structure
```python
SubQuestionResult(
    question="What is the role of phonons in room-temperature superconductivity?",
    hypothesis="Phonon-mediated Cooper pair formation at room temperature is enabled by...",
    confidence=0.78,
    quality_score=0.82,
    generation=1,           # 0 = initial, 1+ = evolved
    evidence=["...", "..."],
    contradictions=[],
    context_used=True,      # True if Qdrant context was injected
    semantic_continuity=0.64
)
```

---

## 7. MemoryAgent

**File:** `src/agents/memory_agent.py`  
**Type:** `ReactiveSubscriber` (not `BaseAgent`)  
**Purpose:** Persistently store high-confidence research findings without coupling to producers.

MemoryAgent is **not a cognitive agent** — it is a reactive infrastructure agent. It does not produce hypotheses or reason. It only listens to events and persists.

### Registration

```python
memory_agent = MemoryAgent(research_memory=research_memory)
memory_agent.register(event_bus)
# Now subscribed to: "hypothesis.generated", "synthesis.ready"
```

### Event Handling

```python
async def handle_event(self, event: RuntimeEvent) -> None:
    payload = event.payload
    entry = MemoryEntry(
        topic=payload.get("topic", ""),
        statement=payload.get("statement", ""),
        confidence=payload.get("confidence", 0.5),
        source=payload.get("source", "memory_agent"),
        session_id=payload.get("session_id"),
        evidence=payload.get("evidence", []),
        generation=payload.get("generation", 0)
    )
    # Only persist if confidence >= threshold (default 0.5)
    if entry.confidence >= self.min_confidence:
        await self.research_memory.store(entry)
```

### Subscribed Topics

| Topic | Action |
|-------|--------|
| `hypothesis.generated` | Store hypothesis to ResearchMemory |
| `synthesis.ready` | Store synthesis conclusion to ResearchMemory |

---

## 8. Agent Configuration & Construction

### Minimal (Heuristic Mode)
```python
agent = HypothesisAgent(agent_id="h_001")
# No inference_router → heuristic generation
# No event_bus → no event publishing
# No governance → no policy enforcement
```

### Production (Full Stack)
```python
agent = HypothesisAgent(
    agent_id="h_001",
    inference_router=InferenceRouter(providers=[...], reasoning_trace=trace),
    event_bus=RedisEventBus(redis_client=redis),
    governance=PolicyEnforcer(audit_log=audit_log),
    reasoning_trace=ReasoningTrace(redis_client=redis, session_factory=pg_factory),
    memory=research_memory,
    context_engine=context_engine,
)
```

---

## 9. AgentSpawner

**File:** `src/runtime/agent_spawner.py`  
**Purpose:** Runtime creation of agents with consistent dependency wiring.

```python
spawner = AgentSpawner(
    inference_router=router,
    event_bus=event_bus,
    governance=policy_enforcer,
    reasoning_trace=trace,
    memory=research_memory,
    context_engine=context_engine,
)

# Spawn by type
agent = spawner.spawn("hypothesis")   # → HypothesisAgent
agent = spawner.spawn("critique")     # → CritiqueAgent
agent = spawner.spawn("synthesis")    # → SynthesisAgent

# Inject agent into live coordinator
await spawner.scale_coordinator(coordinator, "hypothesis")
# → creates new HypothesisAgent and adds to coordinator's agent pool
```

---

## 10. Inter-Agent Communication Rules

1. **Agents never import other agents** — no direct instantiation of sibling agents
2. **Agents communicate via event bus** — `publish(RuntimeEvent(topic=..., payload=...))`
3. **AgentMessage is the contract** — `run()` always returns `AgentMessage`
4. **MemoryAgent never blocks producers** — event handling is async and isolated
5. **Governance gates all outputs** — PolicyEnforcer evaluates before message leaves run()
6. **Heuristic fallback is mandatory** — every agent must work without InferenceRouter

---

## 11. Event Bus Integration

```python
# Agent publishes (fire-and-forget)
if self.event_bus:
    await self.event_bus.publish(RuntimeEvent(
        topic="hypothesis.generated",
        payload=hypothesis_dict,
        source_agent_id=self.agent_id,
        session_id=context.get("session_id"),
    ))

# ReactiveSubscriber registers
class MemoryAgent(ReactiveSubscriber):
    def register(self, bus: RuntimeEventBus) -> None:
        bus.subscribe("hypothesis.generated", self.handle_event)
        bus.subscribe("synthesis.ready", self.handle_event)
```

---

## 12. Observability

Every agent cycle emits:

**Prometheus Metrics:**
```
irds_runtime_events_total{event_type="agent_cycle_start", agent_type="hypothesis_agent"}
irds_runtime_events_total{event_type="agent_cycle_complete", agent_type="hypothesis_agent"}
irds_active_agents_total
```

**OpenTelemetry Spans:**
```
agent.hypothesis_agent_001.cycle
  attributes:
    agent.id = "hypothesis_agent_001"
    agent.type = "hypothesis_agent"
    session.id = "sess_abc123"
    input.hash = "sha256:..."
    duration_ms = 342
```

**Reasoning Trace:**
```python
ReasoningTrace.record(TraceEntry(
    operation="hypothesis_agent.run",
    input_hash=hash(context),
    output_summary=f"hypothesis generated: confidence={confidence}",
    agent_id=self.agent_id,
    duration_seconds=elapsed
))
```

---

## 13. Adding a New Agent

1. Create `src/agents/{name}_agent.py`
2. Inherit from `BaseAgent`
3. Implement `perceive()`, `reason()`, `act()` — must work without inference_router
4. Define event topic to publish in `act()` if needed
5. Register new topic in `protocols/messages.py` if it's a new topic
6. Add to `AgentSpawner.spawn()` type registry
7. Wire into `lifespan()` in `src/api/main.py`
8. Write tests covering all three lifecycle phases and heuristic mode
9. Run: `pytest && ruff check .` — must pass with 0 errors
