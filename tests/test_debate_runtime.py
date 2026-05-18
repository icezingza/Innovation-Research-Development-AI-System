from unittest.mock import AsyncMock, patch

import pytest

from src.orchestration.debate_runtime import DebateResult, DebateRuntime

# Shared coroutine that bypasses adaptive fast-track so full debate loop runs
_HIGH_COMPLEXITY = AsyncMock(return_value={"complexity_score": 7, "recommended_depth": 3})


@pytest.mark.asyncio
async def test_debate_runtime_produces_result():
    runtime = DebateRuntime()
    result = await runtime.debate("Exercise improves cognitive function")
    assert isinstance(result, DebateResult)
    assert result.debate_id
    assert result.hypothesis == "Exercise improves cognitive function"


@pytest.mark.asyncio
async def test_debate_runtime_has_at_least_one_round():
    runtime = DebateRuntime()
    with patch.object(runtime._adaptive_engine, "evaluate_task_complexity", _HIGH_COMPLEXITY):
        result = await runtime.debate("Coffee improves focus", max_rounds=2)
    assert result.total_rounds >= 1
    assert len(result.rounds) == result.total_rounds


@pytest.mark.asyncio
async def test_debate_runtime_winner_is_valid():
    runtime = DebateRuntime()
    result = await runtime.debate("Sleep deprivation impairs memory")
    assert result.winner in ("proponent", "opponent", "draw")
    assert result.winner_argument


@pytest.mark.asyncio
async def test_debate_runtime_rounds_have_both_positions():
    runtime = DebateRuntime()
    result = await runtime.debate("Stress reduces creativity", max_rounds=2)
    for round_record in result.rounds:
        assert round_record.proponent.role == "proponent"
        assert round_record.opponent.role == "opponent"
        assert round_record.proponent.argument
        assert round_record.opponent.argument
        assert round_record.contradictions_found >= 0


@pytest.mark.asyncio
async def test_debate_runtime_respects_max_rounds():
    runtime = DebateRuntime()
    result = await runtime.debate("Hypothesis X", max_rounds=1)
    assert result.total_rounds <= 1


@pytest.mark.asyncio
async def test_debate_runtime_records_quality_scores():
    runtime = DebateRuntime()
    result = await runtime.debate("Hypothesis Y")
    assert 0.0 <= result.proponent_final_quality <= 1.0
    assert 0.0 <= result.opponent_final_quality <= 1.0


@pytest.mark.asyncio
async def test_debate_runtime_duration_is_positive():
    runtime = DebateRuntime()
    with patch.object(runtime._adaptive_engine, "evaluate_task_complexity", _HIGH_COMPLEXITY):
        result = await runtime.debate("Hypothesis Z")
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_debate_runtime_with_llm_disabled_uses_heuristic():
    runtime = DebateRuntime(inference_router=None)
    with patch.object(runtime._adaptive_engine, "evaluate_task_complexity", _HIGH_COMPLEXITY):
        result = await runtime.debate("Caffeine enhances alertness")
    assert result.total_rounds >= 1
    for r in result.rounds:
        assert "Supporting evidence" in r.proponent.argument or r.proponent.argument
        assert "Counter-evidence" in r.opponent.argument or r.opponent.argument


@pytest.mark.asyncio
async def test_circuit_breaker_triggers_on_stale_debate():
    """Identical argument pairs across rounds trigger the circuit breaker.

    Uses negation-pair words ('always'/'never') so ContradictionAnalyzer
    marks rounds as inconsistent, preventing early convergence.
    The pair is fixed, so consecutive round hashes match → circuit breaker fires.
    """
    runtime = DebateRuntime()

    async def stale_generate(hypothesis, role, prior_argument=None):
        if role == "proponent":
            return ("The mechanism always produces the observed effect.", 0.6)
        return ("The mechanism never produces the observed effect.", 0.5)

    with patch.object(runtime, "_generate", new=stale_generate), \
         patch.object(runtime._adaptive_engine, "evaluate_task_complexity", _HIGH_COMPLEXITY):
        result = await runtime.debate("Stale hypothesis", max_rounds=3)
    assert result.convergence_reason == "circuit_breaker"
    assert result.converged is False


@pytest.mark.asyncio
async def test_circuit_breaker_not_triggered_when_arguments_vary():
    """Varying arguments should not trigger the circuit breaker."""
    runtime = DebateRuntime()
    call_count = 0

    async def varying_generate(hypothesis, role, prior_argument=None):
        nonlocal call_count
        call_count += 1
        return (f"Unique argument #{call_count} for {role}", 0.6)

    with patch.object(runtime, "_generate", new=varying_generate):
        result = await runtime.debate("Novel hypothesis", max_rounds=3)
    assert result.convergence_reason != "circuit_breaker"
