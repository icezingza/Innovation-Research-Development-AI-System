import pytest

from src.reasoning.contradiction_analyzer import ContradictionAnalyzer  # noqa: E402
from src.reasoning.reasoning_trace import ReasoningTrace, TraceEntry
from src.reasoning.reflection_engine import ReflectionEngine
from src.research.hypothesis_evolution import Hypothesis, HypothesisEvolutionEngine


@pytest.mark.asyncio
async def test_reflection_engine_detects_gaps():
    engine = ReflectionEngine()
    result = await engine.reflect({"statement": "X causes Y"})
    assert result.quality_score < 1.0
    assert any("evidence" in g for g in result.gaps)
    assert any("conclusion" in g for g in result.gaps)


@pytest.mark.asyncio
async def test_reflection_engine_recognizes_strengths():
    engine = ReflectionEngine()
    result = await engine.reflect(
        {
            "evidence": ["study A", "study B"],
            "conclusion": "X causes Y",
            "assumptions": ["controlled environment"],
            "confidence": 0.85,
        }
    )
    assert result.quality_score > 0.0
    assert "Evidence-backed claims" in result.strengths
    assert "Explicit confidence scoring" in result.strengths


@pytest.mark.asyncio
async def test_contradiction_analyzer_finds_direct_negation():
    analyzer = ContradictionAnalyzer()
    statements = [
        "The system is always available",
        "The system will never be available",
    ]
    report = await analyzer.analyze(statements)
    assert not report.is_consistent
    assert len(report.contradictions) >= 1
    assert report.contradictions[0].contradiction_type.startswith("direct_negation")


@pytest.mark.asyncio
async def test_contradiction_analyzer_consistent_input():
    analyzer = ContradictionAnalyzer()
    statements = ["The agent processes data", "Results are stored in memory"]
    report = await analyzer.analyze(statements)
    assert report.is_consistent
    assert report.contradictions == []


@pytest.mark.asyncio
async def test_hypothesis_evolution_increments_generation():
    engine = HypothesisEvolutionEngine()
    hypothesis = Hypothesis(
        id="h-1",
        statement="Caffeine improves focus",
        confidence=0.6,
        evidence=["study A"],
        generation=0,
    )
    result = await engine.evolve(hypothesis)
    assert result.evolved.generation == 1
    assert result.evolved.id != hypothesis.id


@pytest.mark.asyncio
async def test_hypothesis_evolution_increases_confidence():
    engine = HypothesisEvolutionEngine()
    hypothesis = Hypothesis(
        id="h-2",
        statement="Exercise reduces stress",
        confidence=0.5,
        evidence=["meta-analysis B"],
        generation=0,
    )
    result = await engine.evolve(hypothesis)
    assert result.evolved.confidence >= hypothesis.confidence


@pytest.mark.asyncio
async def test_reasoning_trace_records_entries():
    trace = ReasoningTrace()
    entry = TraceEntry(
        operation="reflect",
        input_hash=ReasoningTrace.hash_input({"x": 1}),
        output_summary="quality=0.5",
    )
    await trace.record(entry)
    recent = await trace.get_recent()
    assert len(recent) == 1
    assert recent[0].operation == "reflect"
