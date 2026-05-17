"""P1 — Reasoning Quality.

Verifies RecursiveReasoningLoop produces measurable quality improvement
(or at minimum no permanent regression) over recursive cycles using a
deterministic seed prompt.
"""
import pytest


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_recursive_reasoning_improves_quality(api_client):
    payload = {
        "hypothesis_statement": (
            "Distributed cognitive systems improve hypothesis quality "
            "through recursive critique and reflection."
        ),
        "question": "What are the cognitive feedback loops in distributed reasoning systems?",
        "evidence": ["Recursive critique reveals hidden assumptions."],
        "confidence": 0.5,
        "max_depth": 5,
    }
    response = await api_client.post("/reasoning/recursive", json=payload)
    assert response.status_code == 200, response.text

    body = response.json()
    iterations = body["iterations"]
    assert len(iterations) >= 1, "Expected at least 1 iteration"

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
