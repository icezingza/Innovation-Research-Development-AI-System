"""Dimension 4: Memory Tier Consistency (Persistence Level)

ทดสอบ ResearchMemory ในโหมด heuristic (ไม่มี Qdrant/Postgres)
เพื่อยืนยัน:
- store() → buffer เก็บข้อมูลถูกต้อง
- recall() → keyword-overlap fallback ทำงานได้
- ring buffer จำกัดที่ _IN_MEMORY_MAX=2000 entries
- stats() สะท้อนสถานะจริง
"""
import pytest

from src.memory.research_memory import MemoryEntry, ResearchMemory

_IN_MEMORY_MAX = 2000


def _entry(topic: str, statement: str, confidence: float = 0.8) -> MemoryEntry:
    return MemoryEntry(
        topic=topic,
        statement=statement,
        confidence=confidence,
        source="test",
        session_id="test-session",
    )


# ─── Store & Buffer ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_adds_to_buffer():
    memory = ResearchMemory()  # heuristic mode — no external services

    entry = _entry("recursive cognition", "Recursive loops refine hypotheses")
    await memory.store(entry)

    assert len(memory._buffer) == 1
    assert memory._buffer[0].entry_id == entry.entry_id


@pytest.mark.asyncio
async def test_store_multiple_entries_preserves_order():
    memory = ResearchMemory()

    topics = ["alpha", "beta", "gamma"]
    for t in topics:
        await memory.store(_entry(t, f"{t} statement"))

    stored_topics = [e.topic for e in memory._buffer]
    assert stored_topics == topics


@pytest.mark.asyncio
async def test_ring_buffer_does_not_exceed_max():
    memory = ResearchMemory()

    for i in range(_IN_MEMORY_MAX + 50):
        await memory.store(_entry(f"topic-{i}", f"statement {i}"))

    assert len(memory._buffer) == _IN_MEMORY_MAX
    # Most recent entries survive
    assert memory._buffer[-1].topic == f"topic-{_IN_MEMORY_MAX + 49}"


# ─── Recall (keyword-overlap fallback) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_recall_returns_relevant_entry():
    memory = ResearchMemory()

    await memory.store(_entry("distributed systems", "CAP theorem limits consistency"))
    await memory.store(_entry("reinforcement learning", "Reward signals shape agent behavior"))

    results = await memory.recall("distributed systems consistency")

    assert len(results) > 0
    assert any("CAP" in r.statement for r in results)


@pytest.mark.asyncio
async def test_recall_empty_buffer_returns_empty_list():
    memory = ResearchMemory()

    results = await memory.recall("anything")

    assert results == []


@pytest.mark.asyncio
async def test_recall_no_match_returns_empty_list():
    memory = ResearchMemory()

    await memory.store(_entry("quantum physics", "Superposition allows parallel states"))

    results = await memory.recall("cooking recipes")

    assert results == []


@pytest.mark.asyncio
async def test_recall_respects_limit():
    memory = ResearchMemory()

    # Store 10 entries all matching "cognition"
    for i in range(10):
        await memory.store(_entry("cognition", f"cognition finding {i}"))

    results = await memory.recall("cognition", limit=3)

    assert len(results) <= 3


# ─── Stats ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stats_empty_memory():
    memory = ResearchMemory()
    stats = await memory.stats()

    assert stats["total_entries"] == 0
    assert stats["avg_confidence"] == 0.0
    assert stats["qdrant_enabled"] is False
    assert stats["postgres_enabled"] is False


@pytest.mark.asyncio
async def test_stats_reflects_stored_entries():
    memory = ResearchMemory()

    await memory.store(_entry("topic-a", "stmt a", confidence=0.6))
    await memory.store(_entry("topic-b", "stmt b", confidence=0.8))

    stats = await memory.stats()

    assert stats["total_entries"] == 2
    assert stats["avg_confidence"] == pytest.approx(0.7, abs=0.001)
    assert stats["sources"]["test"] == 2


@pytest.mark.asyncio
async def test_get_all_returns_most_recent_first():
    memory = ResearchMemory()

    for i in range(5):
        await memory.store(_entry(f"topic-{i}", f"stmt {i}"))

    entries = await memory.get_all(limit=5)

    # get_all returns reversed (most recent first)
    assert entries[0].topic == "topic-4"
    assert entries[-1].topic == "topic-0"
