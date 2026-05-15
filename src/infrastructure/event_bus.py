import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

from src.telemetry.runtime_metrics import runtime_events

logger = logging.getLogger(__name__)

AsyncHandler = Callable[["RuntimeEvent"], Coroutine[Any, Any, None]]

# Well-known topic constants
TOPIC_HYPOTHESIS_GENERATED = "hypothesis.generated"
TOPIC_HYPOTHESIS_CRITIQUED = "hypothesis.critiqued"
TOPIC_SYNTHESIS_READY = "synthesis.ready"
TOPIC_COORDINATION_STARTED = "coordination.started"
TOPIC_COORDINATION_COMPLETE = "coordination.complete"
TOPIC_WORKFLOW_STARTED = "workflow.started"
TOPIC_WORKFLOW_COMPLETE = "workflow.complete"


class RuntimeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    source_agent_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class RuntimeEventBus:
    """Async pub/sub event bus for inter-agent coordination.

    Supports exact topics ("hypothesis.generated") and prefix wildcards
    ("hypothesis.*" matches any topic starting with "hypothesis.").

    Each handler is called concurrently; a failing handler is logged and
    isolated so it cannot poison other subscribers.

    This is an in-memory implementation. Redis Streams can be substituted
    by replacing publish() and the subscription loop in a future phase.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[AsyncHandler]] = {}
        self._event_count: int = 0

    def subscribe(self, topic: str, handler: AsyncHandler) -> None:
        """Register an async handler for a topic or wildcard pattern."""
        self._subscriptions.setdefault(topic, []).append(handler)
        logger.debug(
            "event_bus_subscribe",
            extra={"topic": topic, "handler": handler.__qualname__},
        )

    def unsubscribe(self, topic: str, handler: AsyncHandler) -> bool:
        handlers = self._subscriptions.get(topic, [])
        try:
            handlers.remove(handler)
            return True
        except ValueError:
            return False

    async def publish(self, event: RuntimeEvent) -> int:
        """Dispatch event to all matching subscribers concurrently.

        Returns the number of handlers invoked.
        """
        matching = self._resolve_handlers(event.topic)
        if not matching:
            return 0

        async def _call(handler: AsyncHandler) -> None:
            try:
                await handler(event)
            except Exception as exc:
                logger.warning(
                    "event_handler_error",
                    extra={
                        "topic": event.topic,
                        "handler": handler.__qualname__,
                        "error": str(exc),
                    },
                )

        await asyncio.gather(*[_call(h) for h in matching])
        self._event_count += 1
        runtime_events.labels(event_type="event_published").inc()
        return len(matching)

    def _resolve_handlers(self, topic: str) -> list[AsyncHandler]:
        result: list[AsyncHandler] = []
        for pattern, handlers in self._subscriptions.items():
            if pattern == topic:
                result.extend(handlers)
            elif pattern.endswith(".*"):
                prefix = pattern[:-2]
                if topic == prefix or topic.startswith(prefix + "."):
                    result.extend(handlers)
            elif pattern == "*":
                result.extend(handlers)
        return result

    @property
    def event_count(self) -> int:
        return self._event_count

    def subscriber_count(self, topic: str | None = None) -> int:
        if topic:
            return len(self._resolve_handlers(topic))
        return sum(len(v) for v in self._subscriptions.values())
