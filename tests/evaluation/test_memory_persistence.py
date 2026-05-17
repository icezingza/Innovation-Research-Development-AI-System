"""P2 — Memory Persistence.

Writes a hypothesis directly to ContextEngine (Qdrant-backed) with a unique
marker, then verifies it can be recalled by semantic similarity in a fresh
build() call. This proves vector memory persists across logical sessions.
"""
import uuid

import pytest


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_hypothesis_recall_via_context_engine(live_app):
    research_memory = live_app.state.research_memory
    context_engine = research_memory._context  # noqa: SLF001

    if context_engine is None:
        pytest.skip("ContextEngine unavailable (Qdrant or embeddings disabled)")
    if not context_engine._embedding.enabled:  # noqa: SLF001
        pytest.skip("Embedding provider disabled")

    marker = uuid.uuid4().hex[:8].upper()
    question = "What are cognitive feedback loops in distributed reasoning?"
    hypothesis = {
        "statement": (
            f"MARKER_{marker}: Recursive reflection refines hypotheses "
            f"via critique feedback loops in distributed cognition."
        ),
        "confidence": 0.9,
        "generation": 0,
    }
    task_id = f"eval-task-{marker}"

    await context_engine.store_hypothesis(
        hypothesis=hypothesis, question=question, task_id=task_id
    )

    # Simulate session restart by clearing the in-memory buffer
    research_memory._buffer.clear()  # noqa: SLF001

    packet = await context_engine.build(question=question, limit=5)

    assert packet.continuity_score > 0.0, (
        f"continuity_score is 0 — nothing recalled from vector memory "
        f"(stored task_id={task_id})"
    )
    assert len(packet.similar_hypotheses) > 0, "No similar hypotheses returned"

    statements = [h.get("statement", "") for h in packet.similar_hypotheses]
    assert any(marker in s for s in statements), (
        f"Marker {marker} not found in recalled statements: {statements!r}"
    )
