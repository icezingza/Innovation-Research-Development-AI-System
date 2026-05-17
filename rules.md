# Development Rules
# Innovation Research & Development AI System (IRDS)

**Version:** 1.0  
**Date:** 2026-05-17

These rules are enforced for all contributions. They exist to protect architectural integrity, cognitive quality, and long-term maintainability of a system designed to evolve for years.

---

## 1. Architecture Rules

### 1.1 Layer Isolation

Every module belongs to exactly one architectural layer. Cross-layer imports must follow the allowed direction:

```
Allowed (→ = may import from):
  api          → orchestration, runtime, memory, governance, inference, security, tenants
  orchestration → agents, reasoning, memory, infrastructure, governance, inference
  agents       → reasoning, memory, infrastructure, inference, protocols
  reasoning    → memory (read-only), inference
  infrastructure → (no upward imports)
  memory       → infrastructure (Redis connector only)
  governance   → infrastructure, protocols
  inference    → (no upward imports)
  security     → infrastructure
  tenants      → (no upward imports)
  protocols    → (no imports)
  telemetry    → (no upward imports)

Forbidden (will be rejected):
  reasoning    → agents
  memory       → orchestration
  inference    → agents
  agents       → orchestration
  governance   → agents (governance is a gate, not a controller)
```

**Rule:** If your import creates a cycle or violates the allowed directions, restructure the code — do not add the import.

### 1.2 Module Placement

| New code type | Correct location |
|--------------|-----------------|
| Runtime logic (scheduling, sessions, streams) | `src/runtime/` |
| Persistent memory logic | `src/memory/` |
| Agent implementations | `src/agents/` |
| Reasoning algorithms | `src/reasoning/` |
| Orchestration workflows | `src/orchestration/` |
| Shared infrastructure (event bus, reactive) | `src/infrastructure/` |
| Governance and policy | `src/governance/` |
| LLM providers and embeddings | `src/inference/` |
| API authentication and rate limiting | `src/security/` |
| Isolated research prototypes | `src/experiments/` |
| New subsystem | `src/{domain}/` before any cross-domain coupling |

### 1.3 No Business Logic in Routes

API routes must only:
- Extract and validate request arguments
- Call a service method from `request.app.state`
- Return a response

Routes must never contain:
- Hypothesis generation logic
- Memory access patterns
- Governance decisions
- Orchestration coordination

### 1.4 No Global Mutable State

All dependencies are injected at construction. No module-level singletons that accumulate state. The only shared state container is `app.state`, populated once during `lifespan()`.

---

## 2. Coding Rules

### 2.1 Type Hints Required Everywhere

```python
# CORRECT
async def recall(self, topic: str, limit: int = 5) -> list[MemoryEntry]: ...

# WRONG — missing return type, missing parameter types
async def recall(self, topic, limit=5): ...
```

`Any` is allowed only when justified by a comment explaining why the type cannot be expressed. Avoid it.

### 2.2 Async-First Design

All I/O must be async. No blocking calls inside cognition flows:

```python
# CORRECT
response = await http_client.post(url, json=payload)
results = await asyncio.gather(task_a(), task_b(), task_c())

# WRONG
response = requests.post(url, json=payload)  # blocks event loop
time.sleep(1)                                # blocks event loop
```

Exception: CPU-bound operations that are already fast (< 1ms) do not need to be async.

### 2.3 Never Silently Swallow Exceptions

```python
# CORRECT — log, re-raise or raise domain error
try:
    result = await qdrant.search(...)
except Exception as e:
    logger.error("qdrant_search_failed", error=str(e), topic=topic)
    raise MemoryBackendError(f"Qdrant search failed: {e}") from e

# WRONG — silent failure hides bugs
try:
    result = await qdrant.search(...)
except Exception:
    return []
```

If degradation is intentional (backend optional), log a WARNING and document the fallback behavior.

### 2.4 Composition Over Inheritance

```python
# CORRECT — compose dependencies
class ResearchAgent(BaseAgent):
    def __init__(self, reflection_engine: ReflectionEngine, evolution_engine: HypothesisEvolutionEngine, ...):
        self._reflection = reflection_engine
        self._evolution = evolution_engine

# WRONG — inherit to reuse behavior
class ResearchAgent(HypothesisAgent, ReflectionMixin, ...):
    ...
```

Multiple inheritance is forbidden unless it's for simple ABC/Protocol interfaces.

### 2.5 Small, Focused Classes

- Files: ideally under 400 lines
- Classes: single responsibility
- Functions: ideally under 50 lines
- If a class is growing beyond its responsibility, extract a collaborator

### 2.6 Descriptive Naming

```python
# CORRECT
async def recall_prior_findings(self, topic: str, limit: int) -> list[MemoryEntry]: ...
confidence_threshold: float = 0.75
session_id: str = generate_session_id()

# WRONG
async def r(self, t, l): ...
ct: float = 0.75
sid: str = gen()
```

No abbreviations unless they are universally understood domain terms (e.g., `id`, `api`, `url`).

### 2.7 No Dead Code

No commented-out code blocks, no `_old` function versions, no `TODO: remove this` left in production files. Remove it or create a tracked backlog item.

### 2.8 No Speculative Abstractions

Implement exactly what the current task requires. Three similar functions are better than a premature generalization. Abstract only when the third instance appears and the pattern is clear.

---

## 3. Comment Rules

### 3.1 Comments Explain WHY, Not WHAT

```python
# CORRECT — explains a non-obvious constraint
# Golden ratio provides natural dampening to prevent confidence overshoot
adjustment = iteration / PHI

# WRONG — restates the code
# Calculate confidence adjustment by dividing iteration by PHI
adjustment = iteration / PHI
```

### 3.2 No Multi-Line Comment Blocks

One short comment line maximum. If you need multiple lines to explain something, the code is too complex — simplify it.

### 3.3 No Docstrings for Obvious Methods

```python
# CORRECT — no docstring needed
async def store(self, entry: MemoryEntry) -> None:
    self._buffer.append(entry)
    ...

# WRONG — restates the signature
async def store(self, entry: MemoryEntry) -> None:
    """Stores a memory entry to the buffer and persistence backends."""
    ...
```

Docstrings are appropriate only for public API methods where the WHY and contract are genuinely non-obvious from the signature.

---

## 4. Agent Rules

### 4.1 Agents Must Work Without External Services

Every agent must implement a heuristic fallback path when `inference_router` is `None`:

```python
async def reason(self, perception: dict) -> dict:
    if self.inference_router:
        result = await self.inference_router.complete(prompt, tier="fast")
        if result:
            return self._parse_llm_result(result)
    return self._heuristic_fallback(perception)
```

### 4.2 Agents Publish Events, Never Call Subscribers

```python
# CORRECT
await self.event_bus.publish(RuntimeEvent(topic="hypothesis.generated", payload=...))

# WRONG
await self.memory_agent.handle(hypothesis)  # direct coupling
await research_memory.store(entry)          # agents don't write to memory directly
```

MemoryAgent registers itself with the event bus. Agents never reference it.

### 4.3 Agents Return AgentMessage

Every `run()` call returns `AgentMessage`. Orchestrators unwrap the content dict from the message. This contract is immutable.

### 4.4 Governance Cannot Be Bypassed

Every agent's `run()` calls `PolicyEnforcer.enforce(message)` when configured. This is not optional and not skippable.

---

## 5. Memory Rules

### 5.1 Multi-Tier Write Is Non-Transactional

Writing to ResearchMemory is a best-effort multi-tier operation. Partial success (e.g., ring buffer succeeds, PostgreSQL fails) is logged but not rolled back. Do not assume atomicity.

### 5.2 Memory Backends Are Optional

Never assume a backend is available. Always handle `None` backend gracefully:

```python
if self._session_factory:
    await self._store_postgres(entry)
# else: silently skip, ring buffer already captured entry
```

### 5.3 Confidentiality of Session Data

Session state must never be logged verbatim. Log session_id only — not goals, findings, or metadata.

---

## 6. Governance Rules

### 6.1 All Agent Actions Are Audited

The GovernanceAuditLog records every PolicyEnforcer decision. This is infrastructure — never remove it or reduce its scope.

### 6.2 DENY Decisions Raise Exceptions

```python
if result.decision == "DENY":
    raise PolicyViolationError(result.reason)
```

Do not continue pipeline execution after a DENY. Do not catch PolicyViolationError and continue silently.

### 6.3 Content Size Limits Are Enforced

Hypotheses with content larger than the configured max_content_bytes receive a WARN or DENY. This prevents unbounded inference token usage.

---

## 7. Inference Rules

### 7.1 Provider Failures Are Logged, Not Raised

When an inference provider fails, log at WARNING level and try the next provider. Raise only when all providers fail:

```python
for provider in providers:
    try:
        response = await provider.complete(request)
        if response.text:
            return response.text
    except Exception as e:
        logger.warning("provider_failed", provider=provider.name, error=str(e))

logger.error("all_providers_failed", tier=tier)
return None  # caller handles heuristic fallback
```

### 7.2 All Inference Calls Are Traced

Every call through InferenceRouter must produce a ReasoningTrace entry with provider, model, tier, latency, and success status.

### 7.3 Never Hardcode Model Names in Agent Code

Model names belong in configuration (`src/config.py` or environment variables). Agents call `inference_router.complete(prompt, tier="fast")` — they never specify a model.

---

## 8. Security Rules

### 8.1 Never Commit Secrets

```bash
# .gitignore must include:
.env
*.env
*.pem
*.key
secrets/
```

API keys, database passwords, and service credentials must only exist in environment variables.

### 8.2 No Hardcoded API Keys

```python
# CORRECT
api_key = settings.openai_api_key  # from environment variable

# WRONG
api_key = "sk-proj-abc123..."     # hardcoded secret — NEVER
```

### 8.3 Constant-Time Comparisons for Secrets

```python
# CORRECT
import hmac
return hmac.compare_digest(provided_key.encode(), valid_key.encode())

# WRONG — timing oracle vulnerability
return provided_key == valid_key
```

### 8.4 Log Sanitization

Never log raw request bodies, API keys, passwords, hypothesis content (can be IP-sensitive), or session goals.

---

## 9. Testing Rules

### 9.1 All New Code Has Tests

Before any PR is merged:
- Every new class has at least one test file
- Every new async method has at least one async test
- Every heuristic fallback path is tested independently of LLM availability
- Every failure mode (backend unavailable, provider failure) is tested

### 9.2 No Fake Placeholder Tests

```python
# WRONG — placeholder with no assertions
def test_agent_exists():
    agent = HypothesisAgent()
    assert agent is not None  # proves nothing

# CORRECT — tests behavior
async def test_hypothesis_agent_heuristic_fallback():
    agent = HypothesisAgent(inference_router=None)
    result = await agent.run({"question": "What causes X?", "session_id": "test"})
    assert result.message_type == MessageType.ACTION
    assert "hypothesis" in result.content
    assert result.content["hypothesis"]["statement"] != ""
```

### 9.3 Async Tests Use pytest-asyncio

```python
import pytest

@pytest.mark.asyncio
async def test_research_memory_store_and_recall():
    memory = ResearchMemory()
    entry = MemoryEntry(topic="test", statement="Test hypothesis", confidence=0.8, ...)
    await memory.store(entry)
    recalled = await memory.recall("test", limit=5)
    assert len(recalled) == 1
    assert recalled[0].statement == "Test hypothesis"
```

### 9.4 Test Isolation

Tests must not share state. Each test creates its own instances. No test modifies a shared database without cleanup. Use in-memory backends (no external services required) for unit tests.

### 9.5 Zero Tolerance

Before any merge: `pytest` must show 0 failures, `ruff check .` must show 0 errors.

---

## 10. Observability Rules

### 10.1 Every Critical Path Has a Metric

New orchestration flows, agent types, and memory operations must emit at least one Prometheus counter or histogram.

### 10.2 Every Agent Cycle Has a Trace Span

`BaseAgent.run()` creates an OTel span automatically. Custom sub-operations within complex agents should create child spans.

### 10.3 Structured Logging Only

```python
# CORRECT
logger.info("hypothesis_generated", agent_id=self.agent_id, confidence=confidence, topic=topic)

# WRONG
logger.info(f"Agent {self.agent_id} generated hypothesis with confidence {confidence} for {topic}")
```

Use a structured logging library. Log key-value pairs, not formatted strings.

---

## 11. Documentation Rules

When introducing a major new subsystem:
1. Update `ROADMAP.md` — mark task complete or add to planned phases
2. Update `ARCHITECTURE.md` — add new component to the system diagram and layer specs
3. Update `PROJECT_STATUS.md` — update current state
4. If the component is user-facing (API endpoint, config option): add to relevant reference doc

Avoid undocumented architectural drift. Every system that grows out of sync with documentation creates technical debt that compounds.

---

## 12. What NOT to Build

The following patterns are explicitly rejected and will not be merged:

| Pattern | Why |
|---------|-----|
| Synchronous blocking I/O in cognition flows | Blocks event loop, destroys async concurrency |
| Global mutable singletons | Creates hidden coupling and test interference |
| Agents that import orchestration | Violates layer isolation |
| LangChain dependency without strong justification | Adds magic abstraction that hides cognitive logic |
| Django or Flask | Wrong framework for async-first architecture |
| `Any` type without justification | Removes type safety from critical paths |
| Commented-out code | Use version control — dead code belongs in git history |
| Placeholder tests with no meaningful assertions | Creates false confidence in test coverage |
| Secrets in source code | Security violation |
| Business logic in API routes | Violates separation of concerns |
| Bypassing PolicyEnforcer | Breaks governance integrity |
| New subsystem without heuristic mode | System must run without external services |
