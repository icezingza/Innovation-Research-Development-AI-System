"""Autonomous research agenda engine.

Analyzes ResearchMemory for under-explored topics (low confidence, few
entries) and generates AgendaItems that can be submitted to AsyncScheduler
for background autonomous investigation.
"""

import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from src.memory.research_memory import ResearchMemory

logger = logging.getLogger(__name__)

_LOW_CONFIDENCE_THRESHOLD = 0.55
_MIN_ENTRIES_FOR_TOPIC = 3
_MAX_AGENDA_ITEMS = 10


class AgendaItem(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    goal: str
    priority: int = 5
    confidence_gap: float
    entry_count: int
    created_at: float = Field(default_factory=time.time)
    status: str = "pending"


class AgendaReport(BaseModel):
    generated_at: float
    total_topics_analyzed: int
    items: list[AgendaItem]
    low_confidence_topics: list[str]
    sparse_topics: list[str]


class ResearchAgenda:
    """Identifies research gaps from ResearchMemory and proposes investigation goals.

    Gap detection heuristics:
    - Low average confidence (<= _LOW_CONFIDENCE_THRESHOLD) → high priority
    - Sparse coverage (<= _MIN_ENTRIES_FOR_TOPIC) → medium priority
    Combined sparse + low confidence → highest priority
    """

    def __init__(self, research_memory: ResearchMemory) -> None:
        self._memory = research_memory
        self._pending_items: list[AgendaItem] = []

    async def analyze(self, limit: int = _MAX_AGENDA_ITEMS) -> AgendaReport:
        """Scan ResearchMemory and generate AgendaItems for identified gaps."""
        all_entries = await self._memory.get_all(limit=500)

        # Group by topic
        by_topic: dict[str, list[Any]] = {}
        for entry in all_entries:
            by_topic.setdefault(entry.topic, []).append(entry)

        items: list[AgendaItem] = []
        low_conf: list[str] = []
        sparse: list[str] = []

        for topic, entries in by_topic.items():
            avg_conf = sum(e.confidence for e in entries) / len(entries)
            count = len(entries)

            is_low_conf = avg_conf <= _LOW_CONFIDENCE_THRESHOLD
            is_sparse = count <= _MIN_ENTRIES_FOR_TOPIC

            if is_low_conf:
                low_conf.append(topic)
            if is_sparse:
                sparse.append(topic)

            if not (is_low_conf or is_sparse):
                continue

            confidence_gap = max(0.0, _LOW_CONFIDENCE_THRESHOLD - avg_conf + 0.1)
            priority = self._compute_priority(is_low_conf, is_sparse, confidence_gap)
            goal = self._generate_goal(topic, avg_conf, count)

            items.append(
                AgendaItem(
                    topic=topic,
                    goal=goal,
                    priority=priority,
                    confidence_gap=round(confidence_gap, 3),
                    entry_count=count,
                )
            )

        items.sort(key=lambda x: (-x.priority, x.confidence_gap), reverse=False)
        items = items[:limit]

        # Replace pending list
        self._pending_items = [i for i in items if i.status == "pending"]

        return AgendaReport(
            generated_at=time.time(),
            total_topics_analyzed=len(by_topic),
            items=items,
            low_confidence_topics=low_conf,
            sparse_topics=sparse,
        )

    def pending_items(self) -> list[AgendaItem]:
        return list(self._pending_items)

    def mark_running(self, item_id: str) -> bool:
        for item in self._pending_items:
            if item.item_id == item_id:
                item.status = "running"
                return True
        return False

    def mark_completed(self, item_id: str) -> bool:
        for item in self._pending_items:
            if item.item_id == item_id:
                item.status = "completed"
                return True
        return False

    def _compute_priority(
        self, is_low_conf: bool, is_sparse: bool, confidence_gap: float
    ) -> int:
        base = 5
        if is_low_conf and is_sparse:
            base = 9
        elif is_low_conf:
            base = 7
        elif is_sparse:
            base = 6
        # Boost by gap magnitude (up to +1)
        if confidence_gap > 0.2:
            base = min(10, base + 1)
        return base

    def _generate_goal(self, topic: str, avg_conf: float, count: int) -> str:
        if avg_conf <= _LOW_CONFIDENCE_THRESHOLD and count <= _MIN_ENTRIES_FOR_TOPIC:
            return (
                f"Conduct comprehensive investigation of '{topic}' to improve "
                f"understanding (current: {count} entries, avg confidence {avg_conf:.2f})"
            )
        if avg_conf <= _LOW_CONFIDENCE_THRESHOLD:
            return (
                f"Deepen analysis of '{topic}' to raise hypothesis confidence "
                f"above {_LOW_CONFIDENCE_THRESHOLD} (current avg: {avg_conf:.2f})"
            )
        return (
            f"Expand research coverage of '{topic}' with additional "
            f"evidence gathering (current: {count} entries)"
        )
