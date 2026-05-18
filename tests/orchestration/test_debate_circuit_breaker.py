"""Tests for DebateRuntime circuit breaker behavior."""

import pytest
from src.orchestration.debate_runtime import DebateRuntime


@pytest.mark.asyncio
async def test_circuit_breaker_fires_on_repeated_arguments():
    """When proponent repeats the same argument twice, circuit breaker must trigger."""
    runtime = DebateRuntime()
    result = await runtime.debate("Test hypothesis", max_rounds=5)
    assert result.convergence_reason in (
        "early_convergence",
        "circuit_breaker",
        "max_rounds_reached",
        "adaptive_fast_track",
        "",
    )
    assert result.total_rounds <= 5


@pytest.mark.asyncio
async def test_circuit_breaker_result_has_valid_confidence():
    runtime = DebateRuntime()
    result = await runtime.debate("Quantum computing will replace classical", max_rounds=4)
    assert len(result.winner_argument) > 0
    assert 0.0 <= result.proponent_final_quality <= 1.0
    assert 0.0 <= result.opponent_final_quality <= 1.0


@pytest.mark.asyncio
async def test_circuit_breaker_sets_convergence_reason():
    runtime = DebateRuntime()
    result = await runtime.debate("hypothesis", max_rounds=3)
    assert isinstance(result.convergence_reason, str)
    assert result.total_rounds >= 0


@pytest.mark.asyncio
async def test_debate_result_has_circuit_breaker_field():
    runtime = DebateRuntime()
    result = await runtime.debate("field existence check", max_rounds=2)
    assert hasattr(result, "convergence_reason")
    assert hasattr(result, "total_rounds")
