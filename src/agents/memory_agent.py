import logging

from src.infrastructure.event_bus import (
    TOPIC_HYPOTHESIS_GENERATED,
    TOPIC_SYNTHESIS_READY,
    RuntimeEvent,
    RuntimeEventBus,
)
from src.infrastructure.reactive_subscriber import ReactiveSubscriber
from src.memory.research_memory import MemoryEntry, ResearchMemory

logger = logging.getLogger(__name__)

_HYPOTHESIS_CONFIDENCE_THRESHOLD = 0.65


class MemoryAgent(ReactiveSubscriber):
    """Persists research findings to ResearchMemory by reacting to bus events.

    Subscribes to:
    - synthesis.ready: persists every synthesis conclusion
    - hypothesis.generated: persists hypotheses above confidence threshold

    This makes knowledge accumulation fully decoupled from the agents and
    coordinators that produce it — they only need to publish events.
    """

    def __init__(self, research_memory: ResearchMemory) -> None:
        self._memory = research_memory

    def register(self, bus: RuntimeEventBus) -> None:
        bus.subscribe(TOPIC_SYNTHESIS_READY, self.handle_event)
        bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, self._on_hypothesis)
        logger.info("memory_agent_registered")

    async def handle_event(self, event: RuntimeEvent) -> None:
        """Handle synthesis.ready events."""
        payload = event.payload
        statement = payload.get("conclusion") or payload.get("statement", "")
        if not statement:
            return

        entry = MemoryEntry(
            topic=payload.get("goal", ""),
            statement=statement,
            confidence=float(payload.get("confidence", 0.5)),
            source="synthesis_agent",
            session_id=event.source_agent_id,
            evidence=[],
            generation=0,
        )
        await self._memory.store(entry)
        logger.info(
            "memory_agent_stored_synthesis",
            extra={"entry_id": entry.entry_id, "topic": entry.topic[:60]},
        )

    async def _on_hypothesis(self, event: RuntimeEvent) -> None:
        payload = event.payload
        confidence = float(payload.get("confidence", 0.0))
        if confidence < _HYPOTHESIS_CONFIDENCE_THRESHOLD:
            return

        statement = payload.get("statement", "")
        if not statement:
            return

        entry = MemoryEntry(
            topic=payload.get("question", ""),
            statement=statement,
            confidence=confidence,
            source="hypothesis_agent",
            session_id=event.source_agent_id,
            evidence=[],
            generation=0,
        )
        await self._memory.store(entry)
