"""Dimension 1: Unit & Functional Testing (Component Level)

ทดสอบ logic ภายใน AgentSpawner และ RuntimeEventBus โดยไม่ต้องพึ่ง
external services — ทุก test ใช้ in-memory เท่านั้น
"""
import pytest

from src.infrastructure.event_bus import RuntimeEvent, RuntimeEventBus
from src.runtime.agent_spawner import AgentSpawner


# ─── AgentSpawner ────────────────────────────────────────────────────────────


def test_spawner_creates_hypothesis_agent():
    bus = RuntimeEventBus()
    spawner = AgentSpawner(event_bus=bus)

    record = spawner.spawn("hypothesis")

    assert record.agent_type == "hypothesis"
    assert record.agent_id.startswith("hypothesis:")
    assert len(spawner.list_agents()) == 1


def test_spawner_creates_all_supported_types():
    bus = RuntimeEventBus()
    spawner = AgentSpawner(event_bus=bus)

    for agent_type in ("hypothesis", "critique", "synthesis", "futurist"):
        spawner.spawn(agent_type)

    stats = spawner.stats()
    assert stats["total_spawned"] == 4
    for agent_type in ("hypothesis", "critique", "synthesis", "futurist"):
        assert stats["by_type"][agent_type] == 1


def test_spawner_rejects_unknown_type():
    spawner = AgentSpawner(event_bus=RuntimeEventBus())

    with pytest.raises(ValueError, match="Unknown agent type"):
        spawner.spawn("oracle")


def test_spawner_terminate_removes_agent():
    spawner = AgentSpawner(event_bus=RuntimeEventBus())
    record = spawner.spawn("critique")

    assert spawner.terminate(record.agent_id) is True
    assert spawner.terminate(record.agent_id) is False  # already removed
    assert spawner.stats()["total_spawned"] == 0


def test_spawner_list_agents_returns_correct_structure():
    spawner = AgentSpawner(event_bus=RuntimeEventBus())
    spawner.spawn("hypothesis")
    spawner.spawn("synthesis")

    agents = spawner.list_agents()
    assert len(agents) == 2
    for a in agents:
        assert "agent_id" in a
        assert "agent_type" in a


# ─── RuntimeEventBus ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_eventbus_publish_reaches_subscriber():
    bus = RuntimeEventBus()
    received: list[RuntimeEvent] = []

    async def handler(event: RuntimeEvent) -> None:
        received.append(event)

    bus.subscribe("hypothesis.generated", handler)
    event = RuntimeEvent(
        topic="hypothesis.generated",
        source_agent_id="HypothesisAgent",
        payload={"confidence": 0.8},
    )
    count = await bus.publish(event)

    assert count == 1
    assert len(received) == 1
    assert received[0].payload["confidence"] == 0.8


@pytest.mark.asyncio
async def test_eventbus_wildcard_subscription():
    bus = RuntimeEventBus()
    received: list[str] = []

    async def handler(event: RuntimeEvent) -> None:
        received.append(event.topic)

    bus.subscribe("hypothesis.*", handler)
    for topic in ("hypothesis.generated", "hypothesis.critiqued"):
        await bus.publish(
            RuntimeEvent(topic=topic, source_agent_id="Agent", payload={})
        )

    assert received == ["hypothesis.generated", "hypothesis.critiqued"]


@pytest.mark.asyncio
async def test_eventbus_no_subscriber_returns_zero():
    bus = RuntimeEventBus()
    event = RuntimeEvent(topic="unsubscribed.topic", source_agent_id="X", payload={})
    count = await bus.publish(event)
    assert count == 0


@pytest.mark.asyncio
async def test_eventbus_unsubscribe_stops_delivery():
    bus = RuntimeEventBus()
    received: list[RuntimeEvent] = []

    async def handler(event: RuntimeEvent) -> None:
        received.append(event)

    bus.subscribe("synthesis.ready", handler)
    bus.unsubscribe("synthesis.ready", handler)

    await bus.publish(
        RuntimeEvent(topic="synthesis.ready", source_agent_id="SynthesisAgent", payload={})
    )
    assert received == []


@pytest.mark.asyncio
async def test_eventbus_event_count_increments():
    bus = RuntimeEventBus()

    async def noop(event: RuntimeEvent) -> None:
        pass

    bus.subscribe("*", noop)
    for _ in range(5):
        await bus.publish(
            RuntimeEvent(topic="any.topic", source_agent_id="Agent", payload={})
        )

    assert bus.event_count == 5
