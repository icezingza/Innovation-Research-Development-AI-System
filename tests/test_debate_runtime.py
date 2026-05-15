import pytest

from src.orchestration.debate_runtime import DebateResult, DebateRuntime


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
    result = await runtime.debate("Hypothesis Z")
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_debate_runtime_with_llm_disabled_uses_heuristic():
    runtime = DebateRuntime(inference_router=None)
    result = await runtime.debate("Caffeine enhances alertness")
    assert result.total_rounds >= 1
    for r in result.rounds:
        assert "Supporting evidence" in r.proponent.argument or r.proponent.argument
        assert "Counter-evidence" in r.opponent.argument or r.opponent.argument
