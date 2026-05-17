"""Tests for ResearchAgenda gap detection and agenda generation."""

import pytest

from src.memory.research_memory import MemoryEntry
from src.orchestration.research_agenda import (
    ResearchAgenda,
)


def _make_entry(
    topic: str, confidence: float, statement: str = "Some hypothesis"
) -> MemoryEntry:
    return MemoryEntry(
        topic=topic,
        statement=statement,
        confidence=confidence,
        source="test",
        session_id="sess-1",
        evidence=[],
        generation=0,
    )


class MockResearchMemory:
    def __init__(self, entries: list[MemoryEntry]) -> None:
        self._entries = entries

    async def get_all(self, limit: int = 500) -> list[MemoryEntry]:
        return self._entries[:limit]

    async def stats(self) -> dict:
        return {"total": len(self._entries)}


class TestResearchAgenda:
    @pytest.mark.asyncio
    async def test_empty_memory_returns_empty_report(self) -> None:
        agenda = ResearchAgenda(MockResearchMemory([]))  # type: ignore[arg-type]
        report = await agenda.analyze()
        assert report.items == []
        assert report.total_topics_analyzed == 0

    @pytest.mark.asyncio
    async def test_low_confidence_topic_flagged(self) -> None:
        entries = [_make_entry("quantum", 0.3) for _ in range(5)]
        agenda = ResearchAgenda(MockResearchMemory(entries))  # type: ignore[arg-type]
        report = await agenda.analyze()
        assert any(i.topic == "quantum" for i in report.items)
        assert "quantum" in report.low_confidence_topics

    @pytest.mark.asyncio
    async def test_sparse_topic_flagged(self) -> None:
        entries = [_make_entry("sparse_topic", 0.9)]  # only 1 entry
        agenda = ResearchAgenda(MockResearchMemory(entries))  # type: ignore[arg-type]
        report = await agenda.analyze()
        assert any(i.topic == "sparse_topic" for i in report.items)
        assert "sparse_topic" in report.sparse_topics

    @pytest.mark.asyncio
    async def test_high_confidence_dense_topic_not_flagged(self) -> None:
        entries = [_make_entry("solid_topic", 0.9) for _ in range(6)]
        agenda = ResearchAgenda(MockResearchMemory(entries))  # type: ignore[arg-type]
        report = await agenda.analyze()
        assert not any(i.topic == "solid_topic" for i in report.items)

    @pytest.mark.asyncio
    async def test_combined_low_confidence_sparse_gets_highest_priority(self) -> None:
        entries = [_make_entry("critical", 0.2)]  # sparse + very low confidence
        agenda = ResearchAgenda(MockResearchMemory(entries))  # type: ignore[arg-type]
        report = await agenda.analyze()
        item = next(i for i in report.items if i.topic == "critical")
        assert item.priority >= 9

    @pytest.mark.asyncio
    async def test_agenda_limit_respected(self) -> None:
        entries = [_make_entry(f"topic_{i}", 0.1) for i in range(20)]
        agenda = ResearchAgenda(MockResearchMemory(entries))  # type: ignore[arg-type]
        report = await agenda.analyze(limit=5)
        assert len(report.items) <= 5

    @pytest.mark.asyncio
    async def test_pending_items_populated(self) -> None:
        entries = [_make_entry("pending_topic", 0.2)]
        agenda = ResearchAgenda(MockResearchMemory(entries))  # type: ignore[arg-type]
        await agenda.analyze()
        pending = agenda.pending_items()
        assert len(pending) >= 1

    @pytest.mark.asyncio
    async def test_mark_running_and_completed(self) -> None:
        entries = [_make_entry("tracked", 0.2)]
        agenda = ResearchAgenda(MockResearchMemory(entries))  # type: ignore[arg-type]
        report = await agenda.analyze()
        item_id = report.items[0].item_id
        assert agenda.mark_running(item_id)
        assert agenda.mark_completed(item_id)

    @pytest.mark.asyncio
    async def test_goal_text_mentions_topic(self) -> None:
        entries = [_make_entry("neuroscience", 0.2)]
        agenda = ResearchAgenda(MockResearchMemory(entries))  # type: ignore[arg-type]
        report = await agenda.analyze()
        assert "neuroscience" in report.items[0].goal
