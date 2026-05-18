# Full System Evaluation Suite — Design Spec
**Date:** 2026-05-18
**Scope:** End-to-end correctness, reasoning accuracy, memory persistence, and performance measurement for the Innovation-Research-Development-AI-System (NRE v5.0.0)

---

## 1. Objective

Produce a repeatable, quantitative evaluation of the full cognitive infrastructure stack running on Docker Compose. The evaluation answers four questions in priority order:

1. Does the reasoning pipeline produce measurably better hypotheses over recursive cycles?
2. Does memory persist correctly and recall accurately across sessions?
3. Are all API endpoints correct under real HTTP load?
4. Are latency and throughput within acceptable bounds?

---

## 2. Evaluation Architecture

### 2.1 Three-Phase Pipeline

```
Phase 1: Infra Readiness
  docker compose up -d
  wait for healthchecks (postgres, redis, qdrant, neo4j)
  alembic upgrade head
  GET /health → assert status=healthy

Phase 2: pytest Evaluation Suite
  tests/evaluation/test_reasoning_quality.py   (P1)
  tests/evaluation/test_memory_persistence.py  (P2)
  tests/evaluation/test_api_correctness.py     (P3)
  tests/evaluation/test_performance.py         (P4)

Phase 3: Report Generation
  scripts/evaluate_system.py collects pytest JSON output
  writes evaluation_report.json  (machine-readable)
  writes evaluation_report.html  (human-readable dashboard)
```

### 2.2 File Layout

```
tests/evaluation/
├── conftest.py                    ← shared fixtures
├── test_reasoning_quality.py      ← P1
├── test_memory_persistence.py     ← P2
├── test_api_correctness.py        ← P3
└── test_performance.py            ← P4

scripts/
└── evaluate_system.py             ← CLI orchestrator

.env.evaluation                    ← test environment config
```

---

## 3. Dimension Specifications

### P1 — Reasoning Quality

**What is measured:** Whether `RecursiveReasoningLoop` produces a measurable improvement in hypothesis quality score over N iterations via `QualityTracker`.

**Test flow:**
1. Instantiate `RecursiveReasoningLoop` with `max_depth=5` against live services.
2. Run loop on a fixed research question (deterministic seed prompt).
3. Collect `quality_score` per cycle from `ReasoningTrace`.
4. Assert quality trend is not permanently `declining`.

**Pass criteria:**
- At least 1 cycle with `trend = improving`
- No 3 consecutive cycles with `trend = declining`
- Final score ≥ initial score

**Failure output:** Per-cycle quality scores + trend labels printed to report.

---

### P2 — Memory Persistence

**What is measured:** Whether a hypothesis written to `ResearchMemory` (Qdrant + PostgreSQL) can be recalled with high cosine similarity in a new session.

**Test flow:**
1. Write a hypothesis with known content via `ResearchMemory.store()`.
2. Dispose the in-memory session (simulate restart).
3. Re-instantiate `ContextEngine` with same Qdrant connection.
4. Query with the original research question as embedding.
5. Assert top-1 recalled chunk similarity ≥ 0.75.

**Pass criteria:**
- Recall top-1 cosine similarity ≥ 0.75
- Hypothesis metadata (id, session_id) matches persisted record in PostgreSQL

**Failure output:** Retrieved similarity score + nearest neighbour content diff.

---

### P3 — API Correctness

**What is measured:** Every registered FastAPI route returns the correct HTTP status and a response body that validates against the declared Pydantic schema.

**Test flow:**
1. Start server via `httpx.AsyncClient(app=app, base_url="http://test")`.
2. Call every route documented in `src/api/routes/` with minimal valid payloads.
3. Assert status codes match route contract (200/202/404 as appropriate).
4. Parse response JSON and validate required fields are present.

**Routes covered:**
`/health`, `/research/tasks`, `/workflows`, `/runtime/state`, `/reasoning/traces`,
`/reasoning/recursive`, `/reasoning/debate`, `/governance/audit`, `/cognition/coordinate`,
`/intelligence/report`, `/intelligence/recall`, `/sessions`, `/tenants`, `/auth/register`,
`/auth/login`, `/dashboard/metrics`, `/agenda`

**Pass criteria:**
- 0 unexpected 5xx responses
- 0 missing required response fields
- All 202 responses include a `task_id` or `workflow_id`

---

### P4 — Performance & Latency

**What is measured:** End-to-end wall-clock timing of key cognitive operations and event bus throughput.

**Benchmarks (pytest-benchmark):**

| Benchmark | Target | Hard Fail |
|---|---|---|
| `/health` round-trip | < 50ms | > 200ms |
| `AgentCoordinator.coordinate()` (heuristic) | < 10s | > 30s |
| `ResearchWorkflow.execute()` (heuristic) | < 20s | > 60s |
| `RuntimeEventBus` publish 1000 events | < 1s | > 5s |
| `ContextEngine.recall()` (Qdrant) | < 500ms | > 2s |

**Test flow:**
1. Run each operation 3 times (warmup=1, rounds=3).
2. Record mean, min, max via `pytest-benchmark`.
3. Assert mean < target, hard-fail if mean > hard fail threshold.

---

## 4. Shared Test Infrastructure

### conftest.py fixtures

```python
# Key fixtures (signatures only — implementation in plan)

@pytest.fixture(scope="session")
async def live_app() -> AsyncGenerator[FastAPI, None]:
    # yields app with full lifespan (real services)

@pytest.fixture(scope="session")
async def api_client(live_app) -> AsyncGenerator[AsyncClient, None]:
    # yields httpx.AsyncClient pointed at live_app

@pytest.fixture(scope="session")
def require_services():
    # pytest.skip() if Docker services are not reachable
    # checks: redis, postgres, qdrant, neo4j ports

@pytest.fixture
async def clean_db(live_app):
    # truncates test rows after each test
```

All evaluation tests are marked `@pytest.mark.integration` and require `require_services`.

---

## 5. Evaluation Report Schema

### evaluation_report.json

```json
{
  "timestamp": "2026-05-18T...",
  "git_sha": "...",
  "services_up": ["redis", "postgres", "qdrant", "neo4j"],
  "dimensions": {
    "reasoning_quality": {
      "passed": true,
      "cycles": 5,
      "initial_score": 0.42,
      "final_score": 0.71,
      "trend_sequence": ["improving", "stable", "improving", "stable", "stable"]
    },
    "memory_persistence": {
      "passed": true,
      "recall_similarity": 0.83,
      "metadata_match": true
    },
    "api_correctness": {
      "passed": true,
      "routes_tested": 17,
      "failures": []
    },
    "performance": {
      "passed": true,
      "benchmarks": { ... }
    }
  },
  "overall": "PASS"
}
```

---

## 6. New Dependencies

Add to `requirements.txt`:
```
pytest-benchmark>=4.0
```

No other new dependencies — `httpx`, `pytest-asyncio`, and Docker Compose are already present.

---

## 7. Environment Config (.env.evaluation)

```bash
POSTGRES_URL=postgresql+asyncpg://cognitive:cognitive@localhost/cognition
REDIS_URL=redis://localhost:6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
# No LLM keys — heuristic mode
OPENAI_API_KEY=
API_KEYS=
RATE_LIMIT_ENABLED=false
```

---

## 8. How to Run

```bash
# 1. Start infra
docker compose up -d
docker compose ps   # wait until all healthy

# 2. Apply migrations
alembic upgrade head

# 3. Run full evaluation
python scripts/evaluate_system.py

# 4. View results
cat evaluation_report.json
open evaluation_report.html   # or start-process on Windows
```

To run a single dimension:
```bash
pytest tests/evaluation/test_reasoning_quality.py -v
pytest tests/evaluation/test_memory_persistence.py -v
pytest tests/evaluation/test_api_correctness.py -v
pytest tests/evaluation/ --benchmark-only -v
```

---

## 9. Out of Scope

- LLM response semantic quality (requires live LLM — deferred to separate benchmark)
- Load/stress testing beyond 4 dimensions above
- Frontend UI testing
- Multi-tenant isolation correctness (covered by existing `tests/test_tenants.py`)
