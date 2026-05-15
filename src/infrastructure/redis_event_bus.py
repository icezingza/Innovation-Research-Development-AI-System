"""Redis Streams-backed event bus for multi-process coordination.

Uses XADD for publishing and XREADGROUP for consumer-group delivery,
enabling distributed workers across multiple processes or hosts.
Falls back gracefully when Redis is unavailable.
"""
import asyncio
import json
import logging
import uuid
from typing import Any

from src.infrastructure.event_bus import (
    RuntimeEvent,
    RuntimeEventBus,
)

logger = logging.getLogger(__name__)

_STREAM_KEY = "cognitive:events"
_CONSUMER_GROUP = "cognitive_workers"
_CONSUMER_PREFIX = "worker"
_BLOCK_MS = 100
_MAX_STREAM_LEN = 10_000


class RedisEventBus(RuntimeEventBus):
    """RuntimeEventBus backed by Redis Streams for distributed multi-process delivery.

    Publishes via XADD and delivers via XREADGROUP so each consumer group
    member receives every message exactly once. Local in-memory subscriptions
    are also honoured for same-process handlers (hybrid mode).
    """

    def __init__(self, redis_client: Any) -> None:
        super().__init__()
        self._redis = redis_client
        self._consumer_id = f"{_CONSUMER_PREFIX}:{uuid.uuid4().hex[:8]}"
        self._listen_task: asyncio.Task | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Ensure the consumer group exists and start the listener loop."""
        try:
            await self._redis.xgroup_create(
                _STREAM_KEY, _CONSUMER_GROUP, id="0", mkstream=True
            )
        except Exception:
            # Group already exists — that's fine
            pass
        self._running = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info("redis_event_bus_started", extra={"consumer": self._consumer_id})

    async def stop(self) -> None:
        self._running = False
        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        logger.info("redis_event_bus_stopped")

    # ------------------------------------------------------------------
    # Publish (override)
    # ------------------------------------------------------------------

    async def publish(self, event: RuntimeEvent) -> int:
        """XADD to Redis stream, then also fan-out locally to in-process handlers."""
        payload = event.model_dump()
        try:
            await self._redis.xadd(
                _STREAM_KEY,
                {"data": json.dumps(payload)},
                maxlen=_MAX_STREAM_LEN,
                approximate=True,
            )
        except Exception as exc:
            logger.warning("redis_publish_failed", extra={"error": str(exc)})

        # Local same-process delivery still works even if Redis fails
        return await super().publish(event)

    # ------------------------------------------------------------------
    # Consumer loop
    # ------------------------------------------------------------------

    async def _listen_loop(self) -> None:
        """Continuously XREADGROUP to deliver cross-process events to local handlers."""
        while self._running:
            try:
                entries = await self._redis.xreadgroup(
                    groupname=_CONSUMER_GROUP,
                    consumername=self._consumer_id,
                    streams={_STREAM_KEY: ">"},
                    count=50,
                    block=_BLOCK_MS,
                )
                if entries:
                    for _stream, messages in entries:
                        for msg_id, fields in messages:
                            await self._dispatch_redis_message(msg_id, fields)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("redis_listen_error", extra={"error": str(exc)})
                await asyncio.sleep(1)

    async def _dispatch_redis_message(self, msg_id: str, fields: dict) -> None:
        try:
            raw = fields.get(b"data") or fields.get("data", "{}")
            if isinstance(raw, bytes):
                raw = raw.decode()
            data = json.loads(raw)
            event = RuntimeEvent(**data)
            handlers = self._resolve_handlers(event.topic)
            await asyncio.gather(
                *[self._call(h, event) for h in handlers], return_exceptions=True
            )
            await self._redis.xack(_STREAM_KEY, _CONSUMER_GROUP, msg_id)
        except Exception as exc:
            logger.warning(
                "redis_message_dispatch_failed",
                extra={"msg_id": str(msg_id), "error": str(exc)},
            )

    # ------------------------------------------------------------------
    # Stats extension
    # ------------------------------------------------------------------

    async def stream_info(self) -> dict[str, Any]:
        try:
            info = await self._redis.xinfo_stream(_STREAM_KEY)
            return {"stream_key": _STREAM_KEY, "length": info.get("length", 0)}
        except Exception:
            return {"stream_key": _STREAM_KEY, "length": 0}


def create_event_bus(redis_client: Any | None = None) -> RuntimeEventBus:
    """Return RedisEventBus if a redis client is provided, else in-memory bus."""
    if redis_client is not None:
        return RedisEventBus(redis_client=redis_client)
    return RuntimeEventBus()
