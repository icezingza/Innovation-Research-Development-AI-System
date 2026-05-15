import pytest

from src.reasoning.recursive_loop import RecursiveConfig, RecursiveReasoningLoop
from src.research.hypothesis_evolution import Hypothesis


def _hypothesis(statement: str = "X causes Y", confidence: float = 0.5) -> Hypothesis:
    import uuid

    return Hypothesis(
        id=str(uuid.uuid4()),
        statement=statement,
        confidence=confidence,
        evidence=["Initial evidence"],
        generation=0,
    )


@pytest.mark.asyncio
async def test_recursive_loop_runs_at_least_one_iteration():
    loop = RecursiveReasoningLoop()
    result = await loop.run(_hypothesis(), question="Does X cause Y?")
    assert result.depth_reached >= 1
    assert result.final_hypothesis.generation >= 1


@pytest.mark.asyncio
async def test_recursive_loop_respects_max_depth():
    # convergence_threshold=1.1 is unreachable, but loop may still stop via
    # no_improvement — either way depth must not exceed max_depth
    config = RecursiveConfig(max_depth=2, convergence_threshold=1.1)
    loop = RecursiveReasoningLoop(config=config)
    result = await loop.run(_hypothesis())
    assert result.depth_reached <= 2
    # convergence_reason is max_depth_reached OR no_improvement (both valid)
    assert result.convergence_reason in ("max_depth_reached", "no_improvement")


@pytest.mark.asyncio
async def test_recursive_loop_converges_on_quality_threshold():
    # Set very low threshold to ensure early convergence
    config = RecursiveConfig(max_depth=10, convergence_threshold=0.01)
    loop = RecursiveReasoningLoop(config=config)
    result = await loop.run(_hypothesis())
    assert result.converged
    assert result.convergence_reason == "quality_threshold_reached"


@pytest.mark.asyncio
async def test_recursive_loop_records_all_iterations():
    config = RecursiveConfig(max_depth=3, convergence_threshold=1.1)
    loop = RecursiveReasoningLoop(config=config)
    result = await loop.run(_hypothesis())
    assert len(result.iterations) == result.depth_reached
    for iteration in result.iterations:
        assert iteration.depth >= 1
        assert 0.0 <= iteration.quality_score <= 1.0


@pytest.mark.asyncio
async def test_recursive_loop_final_hypothesis_is_evolved():
    loop = RecursiveReasoningLoop()
    h = _hypothesis("Sleep affects memory consolidation", confidence=0.6)
    result = await loop.run(h, question="How does sleep affect memory?")
    assert result.final_hypothesis.generation > h.generation
    assert result.final_hypothesis.id != h.id


@pytest.mark.asyncio
async def test_recursive_loop_records_to_trace():
    from src.reasoning.reasoning_trace import ReasoningTrace

    trace = ReasoningTrace()
    config = RecursiveConfig(max_depth=2, convergence_threshold=1.1)
    loop = RecursiveReasoningLoop(config=config, trace=trace)
    await loop.run(_hypothesis())
    recent = await trace.get_recent()
    assert len(recent) >= 1
    assert all(e.operation == "recursive_evolution" for e in recent)


@pytest.mark.asyncio
async def test_recursive_loop_duration_is_positive():
    loop = RecursiveReasoningLoop()
    result = await loop.run(_hypothesis())
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_recursive_loop_question_propagated():
    loop = RecursiveReasoningLoop()
    question = "What drives hypothesis evolution?"
    result = await loop.run(_hypothesis(), question=question)
    assert result.question == question
