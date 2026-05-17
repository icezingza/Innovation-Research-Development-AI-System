"""P4 — Performance & Latency benchmarks.

Approach B (manual timing): we use `time.perf_counter()` inside async tests
to avoid pytest-benchmark vs pytest-asyncio session-scoped event loop
conflicts. Stats are printed via `print()` (run with -s to view).
"""

from __future__ import annotations

import statistics
import time

import pytest

from src.infrastructure.event_bus import RuntimeEvent, RuntimeEventBus


def _summarize(name: str, samples: list[float]) -> tuple[float, float, float]:
    mean = statistics.fmean(samples)
    lo = min(samples)
    hi = max(samples)
    print(
        f"\n[perf:{name}] n={len(samples)} mean={mean:.6f}s min={lo:.6f}s max={hi:.6f}s"
    )
    return mean, lo, hi


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_health_latency(api_client) -> None:
    # Warm-up
    await api_client.get("/health")

    samples: list[float] = []
    for _ in range(20):
        t0 = time.perf_counter()
        resp = await api_client.get("/health")
        samples.append(time.perf_counter() - t0)
        assert resp.status_code == 200

    mean, _, hi = _summarize("health", samples)
    assert hi < 0.2, f"/health hard-fail: max {hi:.3f}s exceeds 200ms"
    if mean >= 0.05:
        print(f"[perf:health] WARNING: mean {mean * 1000:.1f}ms exceeds 50ms target")


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_coordinate_latency(api_client) -> None:
    samples: list[float] = []
    for i in range(3):
        t0 = time.perf_counter()
        resp = await api_client.post(
            "/cognition/coordinate",
            json={"goal": f"What is the role of cognition in research? (run {i})"},
            timeout=60.0,
        )
        samples.append(time.perf_counter() - t0)
        assert resp.status_code == 200

    mean, _, _ = _summarize("coordinate", samples)
    assert mean < 30.0, f"/cognition/coordinate hard-fail: mean {mean:.2f}s exceeds 30s"
    if mean >= 10.0:
        print(f"[perf:coordinate] WARNING: mean {mean:.2f}s exceeds 10s target")


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_event_bus_throughput() -> None:
    bus = RuntimeEventBus()

    async def _noop(event: RuntimeEvent) -> None:
        return None

    bus.subscribe("perf.test", _noop)

    samples: list[float] = []
    for _ in range(3):
        t0 = time.perf_counter()
        for i in range(1000):
            await bus.publish(
                RuntimeEvent(
                    topic="perf.test",
                    source_agent_id="perf-bench",
                    payload={"i": i},
                )
            )
        samples.append(time.perf_counter() - t0)

    mean, _, _ = _summarize("event_bus_1000", samples)
    assert mean < 5.0, (
        f"event bus hard-fail: mean {mean:.3f}s exceeds 5s for 1000 events"
    )
    if mean >= 1.0:
        print(f"[perf:event_bus] WARNING: mean {mean:.3f}s exceeds 1s target")
