"""Dimension 6: Adversarial & Resiliency Testing (Stress Level)

ทดสอบ fault-tolerance infrastructure ในสภาวะวิกฤต:
- CircuitBreaker: CLOSED → OPEN → HALF_OPEN → CLOSED transitions
- RetryHandler: exponential backoff, exhaustion, eventual success
- Graceful heuristic fallback (no external services)
"""
import pytest

from src.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    NamoError,
    RetryConfig,
    RetryHandler,
)


# ─── CircuitBreaker ───────────────────────────────────────────────────────────


def _fast_config(failure_threshold: int = 3) -> CircuitBreakerConfig:
    """Config ที่ตั้ง recovery_timeout=0.0 เพื่อให้ OPEN→HALF_OPEN ทันที"""
    return CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=0.0,
        success_threshold=2,
        timeout=5.0,
    )


@pytest.mark.asyncio
async def test_circuit_starts_closed():
    cb = CircuitBreaker("test", _fast_config())
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_trips_to_open_after_failures():
    cb = CircuitBreaker("db-service", _fast_config(failure_threshold=3))

    async def always_fail():
        raise ConnectionError("DB unreachable")

    for _ in range(3):
        with pytest.raises(Exception):
            await cb.call(always_fail)

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_open_circuit_rejects_immediately_without_calling():
    # recovery_timeout=60s ensures OPEN state doesn't auto-transition during test
    blocking_config = CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=60.0,
        success_threshold=2,
        timeout=5.0,
    )
    cb = CircuitBreaker("llm-service", blocking_config)
    call_count = 0

    async def failing():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("LLM down")

    for _ in range(2):
        with pytest.raises(Exception):
            await cb.call(failing)

    assert cb.state == CircuitState.OPEN
    calls_before_open = call_count

    # Next call should be rejected without invoking the function
    with pytest.raises(NamoError, match="OPEN"):
        await cb.call(failing)

    assert call_count == calls_before_open  # function was NOT called again


@pytest.mark.asyncio
async def test_circuit_recovers_to_closed_after_successes():
    """OPEN → HALF_OPEN → CLOSED หลัง success_threshold=2 successes"""
    cb = CircuitBreaker("recovery-service", _fast_config(failure_threshold=2))

    async def always_fail():
        raise RuntimeError("down")

    async def always_succeed():
        return "ok"

    # Trip to OPEN
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.call(always_fail)

    assert cb.state == CircuitState.OPEN

    # recovery_timeout=0.0 → next call triggers HALF_OPEN
    # success_threshold=2 → need 2 successes to close
    await cb.call(always_succeed)   # HALF_OPEN, success_count=1
    assert cb.state == CircuitState.HALF_OPEN

    await cb.call(always_succeed)   # success_count=2 → CLOSED
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_half_open_failure_trips_back_to_open():
    cb = CircuitBreaker("flaky", _fast_config(failure_threshold=2))

    async def fail():
        raise RuntimeError("still down")

    async def succeed():
        return "ok"

    # Trip to OPEN
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.call(fail)

    # Attempt recovery (HALF_OPEN) then fail again
    with pytest.raises(Exception):
        await cb.call(fail)  # recovery_timeout=0.0 → HALF_OPEN then fail → back to OPEN

    assert cb.state == CircuitState.OPEN


# ─── RetryHandler ─────────────────────────────────────────────────────────────


def _fast_retry(max_attempts: int = 3) -> RetryHandler:
    return RetryHandler(
        config=RetryConfig(
            max_attempts=max_attempts,
            initial_delay=0.001,  # 1ms — fast for tests
            max_delay=0.01,
            jitter=False,
        )
    )


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    handler = _fast_retry(max_attempts=3)
    attempt_log: list[int] = []

    @handler(exceptions=(RuntimeError,))
    async def flaky():
        attempt_log.append(len(attempt_log) + 1)
        if len(attempt_log) < 2:
            raise RuntimeError("not yet")
        return "success"

    result = await flaky()
    assert result == "success"
    assert len(attempt_log) == 2


@pytest.mark.asyncio
async def test_retry_exhausts_all_attempts_and_raises():
    handler = _fast_retry(max_attempts=3)
    attempt_count = 0

    @handler(exceptions=(ValueError,))
    async def always_fail():
        nonlocal attempt_count
        attempt_count += 1
        raise ValueError("permanently broken")

    with pytest.raises(ValueError, match="permanently broken"):
        await always_fail()

    assert attempt_count == 3


@pytest.mark.asyncio
async def test_retry_does_not_catch_unregistered_exception():
    handler = _fast_retry(max_attempts=3)
    attempt_count = 0

    @handler(exceptions=(ValueError,))  # only catches ValueError
    async def raises_type_error():
        nonlocal attempt_count
        attempt_count += 1
        raise TypeError("wrong type")

    with pytest.raises(TypeError):
        await raises_type_error()

    assert attempt_count == 1  # no retry for unregistered exception type


@pytest.mark.asyncio
async def test_retry_on_retry_callback_invoked():
    handler = _fast_retry(max_attempts=3)
    retry_log: list[int] = []

    def on_retry(attempt: int, _exc: Exception) -> None:
        retry_log.append(attempt)

    @handler(exceptions=(RuntimeError,), on_retry=on_retry)
    async def fails_twice():
        if len(retry_log) < 2:
            raise RuntimeError("retry me")
        return "done"

    await fails_twice()
    assert retry_log == [0, 1]  # retried on attempts 0 and 1


# ─── Heuristic Fallback (no external services) ───────────────────────────────


@pytest.mark.asyncio
async def test_research_memory_heuristic_mode_no_crash():
    """ระบบต้องทำงานได้โดยไม่ต้องมี Qdrant หรือ Postgres"""
    from src.memory.research_memory import MemoryEntry, ResearchMemory

    memory = ResearchMemory(context_engine=None, session_factory=None)
    entry = MemoryEntry(
        topic="chaos engineering",
        statement="Systems must tolerate partial failures gracefully",
        confidence=0.9,
        source="test",
        session_id="chaos-test",
    )
    await memory.store(entry)
    results = await memory.recall("chaos failures")

    assert any("failures" in r.statement or "chaos" in r.topic for r in results)
