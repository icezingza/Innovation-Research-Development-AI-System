import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_QUEUE_MAX = 256


class StreamManager:
    """Bridges in-process events to SSE client queues.

    When a workflow or coordinator runs, it publishes progress dicts here.
    SSE endpoints call create_stream() to get a queue and read from it.

    One workflow_id can have multiple concurrent SSE subscribers (e.g.
    two browser tabs watching the same workflow).
    """

    def __init__(self) -> None:
        self._streams: dict[str, list[asyncio.Queue]] = {}

    def create_stream(self, stream_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAX)
        self._streams.setdefault(stream_id, []).append(q)
        logger.debug("stream_created", extra={"stream_id": stream_id})
        return q

    async def publish(self, stream_id: str, event: dict[str, Any]) -> None:
        for q in list(self._streams.get(stream_id, [])):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "stream_queue_full", extra={"stream_id": stream_id}
                )

    async def close(self, stream_id: str) -> None:
        """Signal all subscribers for stream_id that the stream is done."""
        await self.publish(stream_id, {"type": "done", "stream_id": stream_id})

    def cleanup(self, stream_id: str, queue: asyncio.Queue) -> None:
        streams = self._streams.get(stream_id, [])
        try:
            streams.remove(queue)
        except ValueError:
            pass
        if not streams:
            self._streams.pop(stream_id, None)

    def active_streams(self) -> dict[str, int]:
        return {sid: len(qs) for sid, qs in self._streams.items() if qs}
