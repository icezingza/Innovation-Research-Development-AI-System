# Full System Evaluation Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pytest-based 4-dimension evaluation suite that runs against live Docker Compose services and produces a quantitative JSON+HTML report.

**Architecture:** New `tests/evaluation/` package gated by a service-probe fixture, plus a `scripts/evaluate_system.py` CLI orchestrator. Each dimension (reasoning quality / memory persistence / API correctness / performance) lives in its own test file with explicit pass criteria.

**Tech Stack:** pytest, pytest-asyncio, pytest-benchmark, httpx, FastAPI lifespan, Docker Compose (Redis/Postgres/Qdrant/Neo4j).

**Spec reference:** [docs/superpowers/specs/2026-05-18-fullsystem-evaluation-design.md](../specs/2026-05-18-fullsystem-evaluation-design.md)

---

## Task 1: Add Dependency and Environment Config

**Files:**
- Modify: `requirements.txt`
- Create: `.env.evaluation`

- [ ] **Step 1: Add pytest-benchmark to requirements.txt**

Append the following line to the end of `requirements.txt`:

```
pytest-benchmark>=4.0
```

- [ ] **Step 2: Create `.env.evaluation`**

Create file `.env.evaluation` at repo root with:

```bash
POSTGRES_URL=postgresql+asyncpg://cognitive:cognitive@localhost/cognition
REDIS_URL=redis://localhost:6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
OPENAI_API_KEY=
API_KEYS=
RATE_LIMIT_ENABLED=false
LOG_LEVEL=WARNING
```

- [ ] **Step 3: Install the new dependency**

Run: `pip install pytest-benchmark>=4.0`
Expected: Successfully installed pytest-benchmark-4.x.x

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .env.evaluation
git commit -m "chore: add pytest-benchmark + evaluation env config"
```

---

## Task 2: Evaluation Package Scaffold + Service-Probe Fixture

**Files:**
- Create: `tests/evaluation/__init__.py`
- Create: `tests/evaluation/conftest.py`
- Create: `tests/evaluation/test_smoke.py`

- [ ] **Step 1: Create the package init file**

Create `tests/evaluation/__init__.py` (empty file).

- [ ] **Step 2: Write the failing smoke test**

Create `tests/evaluation/test_smoke.py`:

```python
"""Smoke test: verify evaluation fixtures wire up correctly."""
import pytest


@pytest.mark.integration
def test_require_services_fixture_runs(require_services):
    assert require_services["redis"] is True
    assert require_services["postgres"] is True
    assert require_services["qdrant"] is True
    assert require_services["neo4j"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_client_health(api_client):
    response = await api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

- [ ] **Step 3: Run smoke test to verify it fails**

Run: `pytest tests/evaluation/test_smoke.py -v`
Expected: FAIL — fixture `require_services` not found

- [ ] **Step 4: Write the conftest with fixtures**

Create `tests/evaluation/conftest.py`:

```python
"""Shared fixtures for the full-system evaluation suite.

All evaluation tests require live Docker Compose services
(redis, postgres, qdrant, neo4j). The `require_services` fixture
probes each service and skips the test session if any are down.
"""
import asyncio
import os
import socket
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


_SERVICE_PORTS = {
    "redis": ("localhost", 6379),
    "postgres": ("localhost", 5432),
    "qdrant": ("localhost", 6333),
    "neo4j": ("localhost", 7687),
}


def _probe_port(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


@pytest.fixture(scope="session")
def require_services() -> dict[str, bool]:
    """Skip the test if any required Docker service is unreachable."""
    results = {
        name: _probe_port(host, port)
        for name, (host, port) in _SERVICE_PORTS.items()
    }
    missing = [name for name, ok in results.items() if not ok]
    if missing:
        pytest.skip(
            f"Required services unreachable: {missing}. "
            f"Run `docker compose up -d` first."
        )
    return results


@pytest_asyncio.fixture(scope="session")
async def live_app(require_services):
    """Construct the FastAPI app with its real lifespan against live services."""
    # Force .env.evaluation values into process env before app/lifespan boots
    os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://cognitive:cognitive@localhost/cognition")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    os.environ.setdefault("QDRANT_HOST", "localhost")
    os.environ.setdefault("QDRANT_PORT", "6333")
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
    os.environ.setdefault("NEO4J_USER", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "password")

    app = create_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest_asyncio.fixture(scope="session")
async def api_client(live_app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=live_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

- [ ] **Step 5: Register the `integration` marker**

Append to `pytest.ini` (or `pyproject.toml` if pytest config lives there) under `[pytest]` markers section:

```ini
[pytest]
markers =
    integration: requires live Docker Compose services
asyncio_mode = auto
```

If `pytest.ini` does not exist, create it with the content above.

- [ ] **Step 6: Start Docker Compose**

Run: `docker compose up -d`
Wait until: `docker compose ps` shows all services with status `(healthy)`.

- [ ] **Step 7: Run smoke test to verify it passes**

Run: `pytest tests/evaluation/test_smoke.py -v`
Expected: 2 passed

- [ ] **Step 8: Commit**

```bash
git add tests/evaluation/__init__.py tests/evaluation/conftest.py tests/evaluation/test_smoke.py pytest.ini
git commit -m "test: scaffold evaluation suite with service-probe fixtures"
```

---

## Task 3: P1 — Reasoning Quality Test

**Files:**
- Create: `tests/evaluation/test_reasoning_quality.py`

- [ ] **Step 1: Write the failing test**

Create `tests/evaluation/test_reasoning_quality.py`:

```python
"""P1 — Reasoning Quality.

Verifies RecursiveReasoningLoop produces measurable quality improvement
over recursive cycles using a deterministic seed prompt.
"""
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recursive_reasoning_improves_quality(api_client):
    payload = {
        "question": "What are the cognitive feedback loops in distributed reasoning systems?",
        "max_depth": 5,
    }
    response = await api_client.post("/reasoning/recursive", json=payload)
    assert response.status_code == 200, response.text

    body = response.json()
    iterations = body["iterations"]
    assert len(iterations) >= 1

    initial_score = iterations[0]["quality_score"]
    final_score = body["final_quality"]

    # Final must be >= initial (no permanent regression)
    assert final_score >= initial_score, (
        f"Final quality {final_score} regressed below initial {initial_score}"
    )

    # No 3 consecutive declining cycles
    consecutive_declines = 0
    prev = initial_score
    max_streak = 0
    for it in iterations[1:]:
        if it["quality_score"] < prev:
            consecutive_declines += 1
            max_streak = max(max_streak, consecutive_declines)
        else:
            consecutive_declines = 0
        prev = it["quality_score"]
    assert max_streak < 3, f"Detected {max_streak} consecutive declines"
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `pytest tests/evaluation/test_reasoning_quality.py -v`
Expected: PASS if the `/reasoning/recursive` endpoint contract matches; otherwise read the error and adjust the JSON keys to match the actual response from `src/api/routes/reasoning.py`. (Inspect: `Grep "recursive" src/api/routes/reasoning.py`.)

- [ ] **Step 3: Commit**

```bash
git add tests/evaluation/test_reasoning_quality.py
git commit -m "test: P1 reasoning quality evaluation"
```

---

## Task 4: P2 — Memory Persistence Test

**Files:**
- Create: `tests/evaluation/test_memory_persistence.py`

- [ ] **Step 1: Write the failing test**

Create `tests/evaluation/test_memory_persistence.py`:

```python
"""P2 — Memory Persistence.

Writes a hypothesis to ResearchMemory (Qdrant + Postgres), simulates session
restart by clearing the in-memory ring buffer, then verifies recall via
ContextEngine returns the same record with cosine similarity >= 0.75.
"""
import uuid

import pytest

from src.memory.research_memory import MemoryEntry


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hypothesis_recall_across_sessions(live_app):
    research_memory = live_app.state.research_memory
    context_engine = live_app.state.research_memory._context_engine  # noqa: SLF001

    if context_engine is None:
        pytest.skip("ContextEngine unavailable (Qdrant or embeddings disabled)")

    marker = f"FEEDBACK_LOOPS_{uuid.uuid4().hex[:8]}"
    entry = MemoryEntry(
        topic="Cognitive feedback loops",
        statement=f"{marker}: Recursive reflection refines hypotheses via critique.",
        confidence=0.9,
        source="evaluation",
        session_id="eval-session-1",
        evidence=["test fixture"],
    )
    await research_memory.store(entry)

    # Clear in-memory ring buffer to force vector recall path
    research_memory._buffer.clear()  # noqa: SLF001

    recalled = await context_engine.recall(
        query="cognitive feedback loops recursive reflection",
        limit=3,
    )

    assert len(recalled) > 0, "Recall returned no results"
    top = recalled[0]
    assert top.score >= 0.75, f"Top similarity {top.score} below threshold"
    assert marker in top.content, (
        f"Recalled content does not contain marker: {top.content!r}"
    )
```

- [ ] **Step 2: Run test**

Run: `pytest tests/evaluation/test_memory_persistence.py -v`
Expected: PASS. If the attribute name `_context_engine` or `_buffer` differs, run `Grep "context_engine" src/memory/research_memory.py` and adjust.

- [ ] **Step 3: Commit**

```bash
git add tests/evaluation/test_memory_persistence.py
git commit -m "test: P2 memory persistence and recall accuracy"
```

---

## Task 5: P3 — API Correctness Test

**Files:**
- Create: `tests/evaluation/test_api_correctness.py`

- [ ] **Step 1: Write the test**

Create `tests/evaluation/test_api_correctness.py`:

```python
"""P3 — API Correctness.

Exercises every public route with a minimal valid payload and asserts
status code + presence of required response fields.
"""
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint(api_client):
    r = await api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_runtime_state(api_client):
    r = await api_client.get("/runtime/state")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_task_lifecycle(api_client):
    create = await api_client.post(
        "/research/tasks",
        json={"question": "What is recursive cognition?"},
    )
    assert create.status_code == 202, create.text
    task_id = create.json()["task_id"]

    fetch = await api_client.get(f"/research/tasks/{task_id}")
    assert fetch.status_code in (200, 202)
    assert fetch.json()["task_id"] == task_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_lifecycle(api_client):
    create = await api_client.post(
        "/workflows",
        json={"goal": "Test workflow goal"},
    )
    assert create.status_code == 202, create.text
    wf_id = create.json()["workflow_id"]

    fetch = await api_client.get(f"/workflows/{wf_id}")
    assert fetch.status_code in (200, 202)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recursive_reasoning_endpoint(api_client):
    r = await api_client.post(
        "/reasoning/recursive",
        json={"question": "Test question", "max_depth": 2},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "final_quality" in body
    assert "iterations" in body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_debate_endpoint(api_client):
    r = await api_client.post(
        "/reasoning/debate",
        json={"topic": "Persistent memory vs ephemeral state"},
    )
    assert r.status_code == 200, r.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_governance_audit(api_client):
    r = await api_client.get("/governance/audit")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_intelligence_report(api_client):
    r = await api_client.get("/intelligence/report")
    assert r.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_intelligence_recall(api_client):
    r = await api_client.post(
        "/intelligence/recall",
        json={"query": "recursive cognition"},
    )
    assert r.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinate_endpoint(api_client):
    r = await api_client.post(
        "/cognition/coordinate",
        json={"question": "Coordinate this question"},
    )
    assert r.status_code == 200, r.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_streams_active(api_client):
    r = await api_client.get("/streams/active")
    assert r.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dashboard_metrics(api_client):
    r = await api_client.get("/dashboard/metrics")
    assert r.status_code in (200, 401)  # may require auth


@pytest.mark.integration
@pytest.mark.asyncio
async def test_no_unexpected_5xx_on_invalid_input(api_client):
    """Bad input should return 4xx, never 5xx."""
    r = await api_client.post("/workflows", json={})
    assert r.status_code < 500, f"Got 5xx on empty payload: {r.status_code}"
```

- [ ] **Step 2: Run tests; adjust per real route contracts**

Run: `pytest tests/evaluation/test_api_correctness.py -v`
Expected: Most pass. For any failure, inspect the matching route in `src/api/routes/<name>.py`, adjust the test payload or assertion to match the real contract, and re-run.

- [ ] **Step 3: Commit**

```bash
git add tests/evaluation/test_api_correctness.py
git commit -m "test: P3 API correctness across all public routes"
```

---

## Task 6: P4 — Performance Benchmarks

**Files:**
- Create: `tests/evaluation/test_performance.py`

- [ ] **Step 1: Write the benchmarks**

Create `tests/evaluation/test_performance.py`:

```python
"""P4 — Performance & Latency.

Uses pytest-benchmark for statistical timing. Hard fail thresholds match
the design spec (Section 3, P4).
"""
import asyncio

import pytest

from src.infrastructure.event_bus import RuntimeEventBus


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_latency(api_client, benchmark):
    async def _call():
        r = await api_client.get("/health")
        assert r.status_code == 200

    def runner():
        asyncio.get_event_loop().run_until_complete(_call())

    benchmark.pedantic(runner, rounds=3, warmup_rounds=1)
    assert benchmark.stats["mean"] < 0.2, "health latency > 200ms hard fail"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinate_latency(api_client, benchmark):
    async def _call():
        r = await api_client.post(
            "/cognition/coordinate",
            json={"question": "Benchmark question"},
        )
        assert r.status_code == 200

    def runner():
        asyncio.get_event_loop().run_until_complete(_call())

    benchmark.pedantic(runner, rounds=3, warmup_rounds=1)
    assert benchmark.stats["mean"] < 30.0, "coordinate latency > 30s hard fail"


@pytest.mark.integration
def test_event_bus_throughput(benchmark):
    async def _publish_1000():
        bus = RuntimeEventBus()
        for i in range(1000):
            await bus.publish("benchmark.event", {"i": i})

    def runner():
        asyncio.new_event_loop().run_until_complete(_publish_1000())

    benchmark.pedantic(runner, rounds=3, warmup_rounds=1)
    assert benchmark.stats["mean"] < 5.0, "1000-event publish > 5s hard fail"
```

- [ ] **Step 2: Run benchmarks**

Run: `pytest tests/evaluation/test_performance.py -v --benchmark-only`
Expected: All 3 benchmarks pass within hard-fail thresholds. Note printed mean/min/max.

- [ ] **Step 3: Commit**

```bash
git add tests/evaluation/test_performance.py
git commit -m "test: P4 performance and latency benchmarks"
```

---

## Task 7: Evaluation CLI Orchestrator

**Files:**
- Create: `scripts/evaluate_system.py`

- [ ] **Step 1: Write the CLI script**

Create `scripts/evaluate_system.py`:

```python
"""Full system evaluation orchestrator.

Runs the 4-dimension pytest evaluation suite and produces:
- evaluation_report.json (machine-readable)
- evaluation_report.html (human-readable)

Usage:
    python scripts/evaluate_system.py
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_JSON = REPO_ROOT / "evaluation_report.json"
REPORT_HTML = REPO_ROOT / "evaluation_report.html"
PYTEST_JSON = REPO_ROOT / ".pytest_report.json"

SERVICES = {
    "redis": ("localhost", 6379),
    "postgres": ("localhost", 5432),
    "qdrant": ("localhost", 6333),
    "neo4j": ("localhost", 7687),
}


def probe_services() -> dict[str, bool]:
    results = {}
    for name, (host, port) in SERVICES.items():
        try:
            with socket.create_connection((host, port), timeout=1.0):
                results[name] = True
        except OSError:
            results[name] = False
    return results


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def run_pytest(target: str) -> dict:
    """Run a single evaluation file and return parsed pytest output."""
    cmd = [
        sys.executable, "-m", "pytest",
        target,
        "-v",
        "--json-report",
        f"--json-report-file={PYTEST_JSON}",
        "--benchmark-disable" if "performance" not in target else "--benchmark-only",
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if PYTEST_JSON.exists():
        data = json.loads(PYTEST_JSON.read_text())
        PYTEST_JSON.unlink()
    else:
        data = {"summary": {}, "tests": []}
    return {
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "summary": data.get("summary", {}),
        "stdout_tail": proc.stdout[-2000:],
    }


def build_html(report: dict) -> str:
    rows = []
    for dim, result in report["dimensions"].items():
        status = "PASS" if result["passed"] else "FAIL"
        color = "#2ecc71" if result["passed"] else "#e74c3c"
        rows.append(
            f"<tr><td>{dim}</td>"
            f"<td style='color:{color};font-weight:bold'>{status}</td>"
            f"<td>{result['summary'].get('passed', 0)}/"
            f"{result['summary'].get('total', 0)} tests</td></tr>"
        )
    services_html = ", ".join(
        f"<span style='color:{'#2ecc71' if ok else '#e74c3c'}'>{name}</span>"
        for name, ok in report["services"].items()
    )
    return f"""<!doctype html>
<html><head><title>Evaluation Report</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
th {{ background: #f5f5f5; }}
.overall {{ font-size: 24px; padding: 16px; background: {'#d4edda' if report['overall'] == 'PASS' else '#f8d7da'}; }}
</style></head>
<body>
<h1>Full System Evaluation Report</h1>
<p><strong>Timestamp:</strong> {report['timestamp']}</p>
<p><strong>Git SHA:</strong> {report['git_sha']}</p>
<p><strong>Services:</strong> {services_html}</p>
<div class='overall'>Overall: <strong>{report['overall']}</strong></div>
<table>
<thead><tr><th>Dimension</th><th>Status</th><th>Tests</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</body></html>"""


def main() -> int:
    services = probe_services()
    if not all(services.values()):
        missing = [n for n, ok in services.items() if not ok]
        print(f"ERROR: services unreachable: {missing}", file=sys.stderr)
        print("Run `docker compose up -d` and try again.", file=sys.stderr)
        return 2

    targets = {
        "reasoning_quality": "tests/evaluation/test_reasoning_quality.py",
        "memory_persistence": "tests/evaluation/test_memory_persistence.py",
        "api_correctness": "tests/evaluation/test_api_correctness.py",
        "performance": "tests/evaluation/test_performance.py",
    }

    dimensions = {}
    for name, target in targets.items():
        print(f"==> Running {name} ...")
        dimensions[name] = run_pytest(target)

    overall = "PASS" if all(d["passed"] for d in dimensions.values()) else "FAIL"
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "services": services,
        "dimensions": dimensions,
        "overall": overall,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2))
    REPORT_HTML.write_text(build_html(report))
    print(f"\n==> Overall: {overall}")
    print(f"==> JSON: {REPORT_JSON}")
    print(f"==> HTML: {REPORT_HTML}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Install pytest-json-report (required by the CLI)**

Run: `pip install pytest-json-report`
Then append `pytest-json-report` to `requirements.txt`.

- [ ] **Step 3: Run the orchestrator**

Run: `python scripts/evaluate_system.py`
Expected:
- Console output: `==> Running reasoning_quality ...` for each dimension
- `evaluation_report.json` and `evaluation_report.html` created at repo root
- Exit code 0 (PASS) or 1 (FAIL)

- [ ] **Step 4: Verify report contents**

Run: `cat evaluation_report.json | python -m json.tool | head -40`
Expected: JSON with `timestamp`, `git_sha`, `services` (all true), `dimensions` (4 keys), `overall`.

- [ ] **Step 5: Commit**

```bash
git add scripts/evaluate_system.py requirements.txt
git commit -m "feat: add evaluate_system.py CLI orchestrator with JSON+HTML report"
```

---

## Task 8: Document the Workflow in README

**Files:**
- Modify: `README.md` (append a new section)

- [ ] **Step 1: Append usage section to README.md**

Append the following section to the end of `README.md`:

```markdown
## Full System Evaluation

Quantitative end-to-end evaluation of the cognitive infrastructure:

```bash
# 1. Start infrastructure
docker compose up -d
docker compose ps  # wait until all healthy

# 2. Apply DB migrations
alembic upgrade head

# 3. Run full evaluation (4 dimensions)
python scripts/evaluate_system.py

# 4. View results
cat evaluation_report.json
# open evaluation_report.html in a browser
```

Dimensions measured (in priority order):
1. **Reasoning Quality** — `RecursiveReasoningLoop` improvement over cycles
2. **Memory Persistence** — Qdrant/Postgres recall accuracy across sessions
3. **API Correctness** — every route returns valid status + schema
4. **Performance** — health/coordinate latency + event bus throughput

See [docs/superpowers/specs/2026-05-18-fullsystem-evaluation-design.md](docs/superpowers/specs/2026-05-18-fullsystem-evaluation-design.md) for thresholds and pass criteria.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document full system evaluation workflow in README"
```

---

## Final Verification

- [ ] **Run the entire suite once more end-to-end**

```bash
docker compose down -v
docker compose up -d
# wait for all healthy
alembic upgrade head
python scripts/evaluate_system.py
```

Expected:
- Exit code 0
- `evaluation_report.json` shows `"overall": "PASS"`
- All 4 dimensions show `passed: true`
- All 4 services in `services` are `true`

- [ ] **Optional: tag the evaluation baseline**

```bash
git tag eval-baseline-$(date +%Y%m%d)
```
