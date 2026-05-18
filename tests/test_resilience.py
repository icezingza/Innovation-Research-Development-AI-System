import asyncio
import pytest
from typing import Any

from src.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    NamoError,
    DatabaseError,
    RetryHandler,
    RetryConfig,
    FallbackHandler,
)


@pytest.mark.anyio
async def test_circuit_breaker_transitions() -> None:
    """Validate Circuit Breaker state machine transitions and failures."""
    # Configure quick recovery and low threshold for testing speed
    config = CircuitBreakerConfig(
        failure_threshold=2, recovery_timeout=0.1, success_threshold=1, timeout=0.5
    )
    cb = CircuitBreaker("test_cb", config)

    # 1. Closed state validation
    assert cb.state == CircuitState.CLOSED

    async def happy_path() -> str:
        return "success"

    res = await cb(happy_path)()
    assert res == "success"
    assert cb.failure_count == 0

    # 2. Failure accumulation & tripping
    async def sad_path() -> None:
        raise ValueError("Simulated network loss")

    with pytest.raises(DatabaseError) as exc_info:
        await cb(sad_path)()
    assert "Simulated network loss" in str(exc_info.value)
    assert cb.failure_count == 1
    assert cb.state == CircuitState.CLOSED

    # Second failure triggers OPEN
    with pytest.raises(DatabaseError):
        await cb(sad_path)()
    assert cb.failure_count == 2
    assert cb.state == CircuitState.OPEN

    # 3. OPEN blocks immediate requests
    with pytest.raises(NamoError) as exc_info:
        await cb(happy_path)()
    assert "is OPEN" in str(exc_info.value)

    # 4. Wait for recovery timeout to transition to HALF-OPEN
    await asyncio.sleep(0.12)

    # Executing now reset the state to HALF-OPEN, and then CLOSED on success
    res2 = await cb(happy_path)()
    assert res2 == "success"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.anyio
async def test_retry_handler_backoff() -> None:
    """Validate Retry Handler exponential backoff and eventual success/failure."""
    config = RetryConfig(
        max_attempts=3, initial_delay=0.01, max_delay=0.1, jitter=False
    )
    retry = RetryHandler(config)

    attempts = []

    async def unreliable_fn() -> str:
        attempts.append(len(attempts))
        if len(attempts) < 3:
            raise KeyError("Failed key")
        return "recovered"

    res = await retry(exceptions=(KeyError,))(unreliable_fn)()
    assert res == "recovered"
    assert len(attempts) == 3


@pytest.mark.anyio
async def test_fallback_handler_staleness() -> None:
    """Validate Fallback Handler cache retrieval on consecutive failures."""
    fallback = FallbackHandler()

    call_count = 0
    trigger_error = False

    # Fallback callable in case of crash
    async def fallback_callable(*args: Any, **kwargs: Any) -> str:
        return "callable_fallback"

    @fallback(fallback_func=fallback_callable)
    async def primary_fn() -> str:
        nonlocal call_count
        call_count += 1
        if trigger_error:
            raise RuntimeError("API dead")
        return f"api_result_{call_count}"

    # 1. Successful execution registers cache
    res1 = await primary_fn()
    assert res1 == "api_result_1"

    # 2. Failure execution triggers custom fallback_callable
    trigger_error = True
    res2 = await primary_fn()
    assert res2 == "callable_fallback"

    # 3. Failure execution without custom fallback (using default wrapper) serves from stale cache
    simple_error = False

    @fallback()
    async def primary_fn_simple() -> str:
        if simple_error:
            raise RuntimeError("Primary crashed")
        return "simple_success"

    await primary_fn_simple()

    # Trigger error uses cached result
    simple_error = True
    res_stale = await primary_fn_simple()
    assert res_stale == "simple_success"
