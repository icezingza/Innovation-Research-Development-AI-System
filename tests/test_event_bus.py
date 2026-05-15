import pytest

from src.infrastructure.event_bus import (
    TOPIC_HYPOTHESIS_GENERATED,
    RuntimeEvent,
    RuntimeEventBus,
)


def _make_event(topic: str = TOPIC_HYPOTHESIS_GENERATED) -> RuntimeEvent:
    return RuntimeEvent(
        topic=topic,
        source_agent_id="test-agent",
        payload={"key": "value"},
    )


@pytest.mark.asyncio
async def test_publish_calls_exact_subscriber():
    bus = RuntimeEventBus()
    received: list[RuntimeEvent] = []

    async def handler(event: RuntimeEvent) -> None:
        received.append(event)

    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, handler)
    count = await bus.publish(_make_event(TOPIC_HYPOTHESIS_GENERATED))
    assert count == 1
    assert len(received) == 1
    assert received[0].topic == TOPIC_HYPOTHESIS_GENERATED


@pytest.mark.asyncio
async def test_wildcard_matches_prefix():
    bus = RuntimeEventBus()
    received: list[str] = []

    async def handler(event: RuntimeEvent) -> None:
        received.append(event.topic)

    bus.subscribe("hypothesis.*", handler)
    await bus.publish(_make_event("hypothesis.generated"))
    await bus.publish(_make_event("hypothesis.critiqued"))
    await bus.publish(_make_event("synthesis.ready"))  # should NOT match
    assert received == ["hypothesis.generated", "hypothesis.critiqued"]


@pytest.mark.asyncio
async def test_global_wildcard_matches_all():
    bus = RuntimeEventBus()
    received: list[str] = []

    async def handler(event: RuntimeEvent) -> None:
        received.append(event.topic)

    bus.subscribe("*", handler)
    await bus.publish(_make_event("hypothesis.generated"))
    await bus.publish(_make_event("synthesis.ready"))
    assert len(received) == 2


@pytest.mark.asyncio
async def test_multiple_subscribers_same_topic():
    bus = RuntimeEventBus()
    calls: list[int] = []

    async def h1(event: RuntimeEvent) -> None:
        calls.append(1)

    async def h2(event: RuntimeEvent) -> None:
        calls.append(2)

    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, h1)
    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, h2)
    await bus.publish(_make_event(TOPIC_HYPOTHESIS_GENERATED))
    assert sorted(calls) == [1, 2]


@pytest.mark.asyncio
async def test_no_subscribers_returns_zero():
    bus = RuntimeEventBus()
    count = await bus.publish(_make_event("unknown.topic"))
    assert count == 0


@pytest.mark.asyncio
async def test_failing_handler_does_not_block_others():
    bus = RuntimeEventBus()
    called: list[str] = []

    async def bad_handler(event: RuntimeEvent) -> None:
        raise RuntimeError("boom")

    async def good_handler(event: RuntimeEvent) -> None:
        called.append("ok")

    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, bad_handler)
    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, good_handler)
    count = await bus.publish(_make_event(TOPIC_HYPOTHESIS_GENERATED))
    assert count == 2
    assert called == ["ok"]


@pytest.mark.asyncio
async def test_unsubscribe_removes_handler():
    bus = RuntimeEventBus()
    called: list[bool] = []

    async def handler(event: RuntimeEvent) -> None:
        called.append(True)

    bus.subscribe(TOPIC_HYPOTHESIS_GENERATED, handler)
    bus.unsubscribe(TOPIC_HYPOTHESIS_GENERATED, handler)
    await bus.publish(_make_event(TOPIC_HYPOTHESIS_GENERATED))
    assert called == []


@pytest.mark.asyncio
async def test_event_count_increments():
    bus = RuntimeEventBus()

    async def noop(event: RuntimeEvent) -> None:
        pass

    bus.subscribe("*", noop)
    assert bus.event_count == 0
    await bus.publish(_make_event("a.b"))
    await bus.publish(_make_event("c.d"))
    assert bus.event_count == 2


@pytest.mark.asyncio
async def test_subscriber_count():
    bus = RuntimeEventBus()

    async def h(event: RuntimeEvent) -> None:
        pass

    assert bus.subscriber_count() == 0
    bus.subscribe("hypothesis.*", h)
    bus.subscribe("synthesis.ready", h)
    assert bus.subscriber_count() == 2
