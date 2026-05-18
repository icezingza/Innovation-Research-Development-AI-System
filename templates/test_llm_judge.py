"""Stage 3: LLM-as-a-Judge (CognitiveJudge)

ทดสอบ CognitiveJudge ใน 2 โหมด:
1. Heuristic (LLM ล่ม) → fallback score ต้อง valid Pydantic schema
2. Schema validation → SynthesisJudgeScore ต้องบังคับ constraints
3. Prompt builder → ต้องมี context ครบ (goal, hypotheses, synthesis)
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from templates.judge import CognitiveJudge, SynthesisJudgeScore


# ─── Schema validation ────────────────────────────────────────────────────────


def test_synthesis_judge_score_valid_schema():
    score = SynthesisJudgeScore(
        accuracy_score=0.9,
        comprehensiveness_score=0.85,
        contradiction_resolution_score=0.75,
        overall_score=0.83,
        rationale="Synthesis accurately reflects all hypotheses.",
        missing_insights=[],
        detected_hallucinations=[],
    )
    assert score.overall_score == pytest.approx(0.83)
    assert score.detected_hallucinations == []


def test_synthesis_judge_score_rejects_out_of_range():
    with pytest.raises(Exception):  # Pydantic v2 raises ValidationError
        SynthesisJudgeScore(
            accuracy_score=1.5,  # violates ge=0, le=1
            comprehensiveness_score=0.8,
            contradiction_resolution_score=0.8,
            overall_score=0.8,
            rationale="bad",
        )


def test_synthesis_judge_score_defaults_empty_lists():
    score = SynthesisJudgeScore(
        accuracy_score=0.7,
        comprehensiveness_score=0.7,
        contradiction_resolution_score=0.7,
        overall_score=0.7,
        rationale="ok",
    )
    assert score.missing_insights == []
    assert score.detected_hallucinations == []


# ─── Prompt builder ───────────────────────────────────────────────────────────


def test_prompt_contains_goal_and_synthesis():
    router = MagicMock()
    judge = CognitiveJudge(router=router)

    goal = "Understand distributed cognition patterns"
    hypotheses = [{"statement": "Agents require shared state", "confidence": 0.8}]
    critiques = [{"contradictions_detected": "State may be inconsistent"}]
    synthesis = {"synthesis_statement": "Distributed agents use consensus protocols"}

    prompt = judge._build_prompt(goal, hypotheses, critiques, synthesis)

    assert goal in prompt
    assert "consensus protocols" in prompt
    assert "Agents require shared state" in prompt
    assert "State may be inconsistent" in prompt


def test_prompt_handles_empty_critiques():
    router = MagicMock()
    judge = CognitiveJudge(router=router)

    prompt = judge._build_prompt(
        goal="Goal",
        hypotheses=[{"statement": "H1", "confidence": 0.5}],
        critiques=[],
        synthesis={"synthesis_statement": "S1"},
    )
    assert "S1" in prompt


# ─── Fallback (heuristic mode) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_judge_returns_fallback_score_when_llm_fails():
    """เมื่อ LLM ไม่พร้อมใช้งาน ระบบต้อง fallback gracefully — ไม่ crash"""
    mock_router = AsyncMock()
    mock_router.complete.side_effect = ConnectionError("LLM service unavailable")

    judge = CognitiveJudge(router=mock_router)
    result = await judge.evaluate_synthesis(
        goal="Test goal",
        hypotheses=[{"statement": "Test hypothesis", "confidence": 0.7}],
        critiques=[],
        synthesis={"synthesis_statement": "Test synthesis"},
    )

    assert isinstance(result, SynthesisJudgeScore)
    assert 0.0 <= result.overall_score <= 1.0
    assert "error" in result.rationale.lower() or "failed" in result.rationale.lower()


@pytest.mark.asyncio
async def test_judge_parses_valid_llm_response():
    """เมื่อ LLM คืน JSON ถูกต้อง ระบบต้อง parse และ return structured score"""
    import json

    expected_json = json.dumps({
        "accuracy_score": 0.92,
        "comprehensiveness_score": 0.88,
        "contradiction_resolution_score": 0.80,
        "overall_score": 0.87,
        "rationale": "Synthesis accurately captures all key hypotheses.",
        "missing_insights": [],
        "detected_hallucinations": [],
    })

    mock_response = MagicMock()
    mock_response.content = expected_json

    mock_router = AsyncMock()
    mock_router.complete.return_value = mock_response

    judge = CognitiveJudge(router=mock_router)
    result = await judge.evaluate_synthesis(
        goal="AI reasoning systems",
        hypotheses=[{"statement": "Recursive loops improve quality", "confidence": 0.85}],
        critiques=[],
        synthesis={"synthesis_statement": "Iterative refinement converges toward truth"},
    )

    assert result.accuracy_score == pytest.approx(0.92)
    assert result.overall_score == pytest.approx(0.87)
    assert result.detected_hallucinations == []
