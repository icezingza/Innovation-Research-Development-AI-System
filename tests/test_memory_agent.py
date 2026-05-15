import pytest

from src.agents.memory_agent import MemoryAgent, _HYPOTHESIS_CONFIDENCE_THRESHOLD
from src.infrastructure.event_bus import (
    TOPIC_HYPOTHESIS_GENERATED,
    TOPIC_SYNTHESIS_READY,
    RuntimeEvent,
    RuntimeEventBus,
)
from src.memory.research_memory import ResearchMemory


def _synthesis_event(goal: str = "Test goal", confidence: float = 0.8) -> RuntimeEvent:
    return RuntimeEvent(
        topic=TOPIC_SYNTHESIS_READY,
        source_agent_id="synthesis-agent-1",
        payload={
            "goal": goal,
            "conclusion": f"Synthesis conclusion for: {goal}",
            "confidence": confidence,
            "source_count": 2,
            "best_hypothesis_id": "h-123",
        },
    )


def _hypothesis_event(
    statement: str = "X causes Y",
    question: str = "Does X cause Y?",
    confidence: float = 0.8,
) -> RuntimeEvent:
    return RuntimeEvent(
        topic=TOPIC_HYPOTHESIS_GENERATED,
        source_agent_id="hypothesis-agent-1",
        payload={
            "question": question,
            "hypothesis_id": "h-456",
            "statement": statement,
            "confidence": confidence,
        },
    )


@pytest.mark.asyncio
async def test_memory_agent_registers_on_bus():
    bus = RuntimeEventBus()
    mem = ResearchMemory()
    agent = MemoryAgent(research_memory=mem)
    agent.register(bus)
    assert bus.subscriber_count(TOPIC_SYNTHESIS_READY) >= 1
    assert bus.subscriber_count(TOPIC_HYPOTHESIS_GENERATED) >= 1


@pytest.mark.asyncio
async def test_memory_agent_stores_synthesis_via_bus():
    bus = RuntimeEventBus()
    mem = ResearchMemory()
    agent = MemoryAgent(research_memory=mem)
    agent.register(bus)

    await bus.publish(_synthesis_event("How does sleep affect memory?"))
    entries = await mem.get_all()
    assert len(entries) == 1
    assert "sleep" in entries[0].topic.lower() or "memory" in entries[0].topic.lower()
    assert entries[0].source == "synthesis_agent"


@pytest.mark.asyncio
async def test_memory_agent_stores_high_confidence_hypothesis():
    bus = RuntimeEventBus()
    mem = ResearchMemory()
    agent = MemoryAgent(research_memory=mem)
    agent.register(bus)

    await bus.publish(
        _hypothesis_event(confidence=_HYPOTHESIS_CONFIDENCE_THRESHOLD + 0.1)
    )
    entries = await mem.get_all()
    assert len(entries) == 1
    assert entries[0].source == "hypothesis_agent"


@pytest.mark.asyncio
async def test_memory_agent_ignores_low_confidence_hypothesis():
    bus = RuntimeEventBus()
    mem = ResearchMemory()
    agent = MemoryAgent(research_memory=mem)
    agent.register(bus)

    await bus.publish(
        _hypothesis_event(confidence=_HYPOTHESIS_CONFIDENCE_THRESHOLD - 0.1)
    )
    entries = await mem.get_all()
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_memory_agent_ignores_empty_synthesis_statement():
    bus = RuntimeEventBus()
    mem = ResearchMemory()
    agent = MemoryAgent(research_memory=mem)
    agent.register(bus)

    event = RuntimeEvent(
        topic=TOPIC_SYNTHESIS_READY,
        source_agent_id="synthesis-agent-1",
        payload={"goal": "test", "conclusion": "", "confidence": 0.8},
    )
    await bus.publish(event)
    entries = await mem.get_all()
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_memory_agent_accumulates_multiple_events():
    bus = RuntimeEventBus()
    mem = ResearchMemory()
    agent = MemoryAgent(research_memory=mem)
    agent.register(bus)

    await bus.publish(_synthesis_event("Goal A"))
    await bus.publish(_synthesis_event("Goal B"))
    await bus.publish(_hypothesis_event(confidence=0.9))
    entries = await mem.get_all()
    assert len(entries) == 3
