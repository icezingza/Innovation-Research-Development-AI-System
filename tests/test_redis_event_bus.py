"""Tests for RedisEventBus and create_event_bus factory."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.event_bus import RuntimeEvent, RuntimeEventBus
from src.infrastructure.redis_event_bus import RedisEventBus, create_event_bus


def _make_event(topic: str = "test.topic") -> RuntimeEvent:
    return RuntimeEvent(topic=topic, source_agent_id="agent-1", payload={"k": "v"})


class TestCreateEventBus:
    def test_returns_in_memory_when_no_client(self) -> None:
        bus = create_event_bus(redis_client=None)
        assert isinstance(bus, RuntimeEventBus)
        assert not isinstance(bus, RedisEventBus)

    def test_returns_redis_bus_with_client(self) -> None:
        mock_client = MagicMock()
        bus = create_event_bus(redis_client=mock_client)
        assert isinstance(bus, RedisEventBus)


class TestRedisEventBus:
    def _make_bus(self) -> tuple[RedisEventBus, MagicMock]:
        client = MagicMock()
        client.xgroup_create = AsyncMock(return_value=True)
        client.xadd = AsyncMock(return_value="1-0")
        client.xreadgroup = AsyncMock(return_value=[])
        client.xack = AsyncMock(return_value=1)
        client.xinfo_stream = AsyncMock(return_value={"length": 5})
        bus = RedisEventBus(redis_client=client)
        return bus, client

    @pytest.mark.asyncio
    async def test_start_creates_consumer_group(self) -> None:
        bus, client = self._make_bus()
        # Make listen loop exit immediately
        client.xreadgroup = AsyncMock(side_effect=asyncio.CancelledError)
        try:
            await bus.start()
        except asyncio.CancelledError:
            pass
        client.xgroup_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_calls_xadd(self) -> None:
        bus, client = self._make_bus()
        event = _make_event()
        await bus.publish(event)
        client.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_delivers_to_local_handlers(self) -> None:
        bus, client = self._make_bus()
        received: list[RuntimeEvent] = []

        async def handler(event: RuntimeEvent) -> None:
            received.append(event)

        bus.subscribe("test.topic", handler)
        await bus.publish(_make_event("test.topic"))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_publish_continues_when_redis_fails(self) -> None:
        bus, client = self._make_bus()
        client.xadd = AsyncMock(side_effect=ConnectionError("redis down"))
        received: list[RuntimeEvent] = []

        async def handler(event: RuntimeEvent) -> None:
            received.append(event)

        bus.subscribe("test.topic", handler)
        await bus.publish(_make_event("test.topic"))
        # Local delivery still works even if Redis XADD failed
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_stop_cancels_listen_task(self) -> None:
        bus, client = self._make_bus()
        client.xreadgroup = AsyncMock(return_value=[])
        await bus.start()
        assert bus._listen_task is not None
        await bus.stop()
        assert bus._listen_task.done()

    @pytest.mark.asyncio
    async def test_stream_info(self) -> None:
        bus, client = self._make_bus()
        info = await bus.stream_info()
        assert info["length"] == 5

    @pytest.mark.asyncio
    async def test_group_already_exists_does_not_raise(self) -> None:
        bus, client = self._make_bus()
        client.xgroup_create = AsyncMock(side_effect=Exception("BUSYGROUP"))
        client.xreadgroup = AsyncMock(side_effect=asyncio.CancelledError)
        # Should not raise
        try:
            await bus.start()
        except asyncio.CancelledError:
            pass
