import pytest

from src.memory.research_memory import MemoryEntry, ResearchMemory


def _entry(
    statement: str = "X causes Y",
    topic: str = "causality",
    confidence: float = 0.75,
    source: str = "synthesis_agent",
    session_id: str = "sess-1",
) -> MemoryEntry:
    return MemoryEntry(
        topic=topic,
        statement=statement,
        confidence=confidence,
        source=source,
        session_id=session_id,
    )


@pytest.mark.asyncio
async def test_store_and_get_all():
    mem = ResearchMemory()
    await mem.store(_entry("Sleep consolidates memory", topic="sleep"))
    await mem.store(_entry("Exercise improves cognition", topic="exercise"))
    entries = await mem.get_all()
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_recall_by_keyword_overlap():
    mem = ResearchMemory()
    await mem.store(_entry("Sleep consolidates episodic memory", topic="sleep memory"))
    await mem.store(_entry("Deep learning requires large datasets", topic="ML"))
    results = await mem.recall("sleep memory consolidation")
    assert len(results) >= 1
    assert "sleep" in results[0].statement.lower() or "memory" in results[0].statement.lower()


@pytest.mark.asyncio
async def test_recall_returns_empty_when_no_match():
    mem = ResearchMemory()
    await mem.store(_entry("Quantum entanglement physics", topic="quantum"))
    results = await mem.recall("exercise cognition running")
    assert results == []


@pytest.mark.asyncio
async def test_recall_respects_limit():
    mem = ResearchMemory()
    for i in range(10):
        await mem.store(_entry(f"hypothesis {i} about memory", topic="memory test"))
    results = await mem.recall("memory hypothesis", limit=3)
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_stats_empty():
    mem = ResearchMemory()
    stats = await mem.stats()
    assert stats["total_entries"] == 0
    assert stats["avg_confidence"] == 0.0


@pytest.mark.asyncio
async def test_stats_with_entries():
    mem = ResearchMemory()
    await mem.store(_entry(confidence=0.8))
    await mem.store(_entry(confidence=0.6))
    stats = await mem.stats()
    assert stats["total_entries"] == 2
    assert abs(stats["avg_confidence"] - 0.7) < 0.01
    assert "synthesis_agent" in stats["sources"]


@pytest.mark.asyncio
async def test_in_memory_ring_buffer_truncates():
    mem = ResearchMemory()
    from src.memory.research_memory import _IN_MEMORY_MAX

    for i in range(_IN_MEMORY_MAX + 50):
        await mem.store(_entry(f"hypothesis {i}", topic="flood"))
    entries = await mem.get_all(limit=_IN_MEMORY_MAX + 50)
    assert len(entries) == _IN_MEMORY_MAX


@pytest.mark.asyncio
async def test_stats_sources_counts():
    mem = ResearchMemory()
    await mem.store(_entry(source="synthesis_agent"))
    await mem.store(_entry(source="hypothesis_agent"))
    await mem.store(_entry(source="synthesis_agent"))
    stats = await mem.stats()
    assert stats["sources"]["synthesis_agent"] == 2
    assert stats["sources"]["hypothesis_agent"] == 1
