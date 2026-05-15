import asyncio
import logging
import time
import uuid
from enum import IntEnum
from typing import Any, Callable, Coroutine

from pydantic import BaseModel

from src.telemetry.runtime_metrics import runtime_events

logger = logging.getLogger(__name__)


class TaskPriority(IntEnum):
    CRITICAL = 1
    HIGH = 3
    NORMAL = 5
    LOW = 7
    BACKGROUND = 10


class ScheduledTask(BaseModel):
    task_id: str
    name: str
    priority: TaskPriority
    submitted_at: float
    status: str = "pending"

    model_config = {"arbitrary_types_allowed": True}


class _QueueEntry:
    """Heap entry: lower value = higher priority. Ties broken by submission time."""

    __slots__ = ("priority", "submitted_at", "task_id", "coro")

    def __init__(
        self,
        priority: int,
        submitted_at: float,
        task_id: str,
        coro: Coroutine[Any, Any, Any],
    ) -> None:
        self.priority = priority
        self.submitted_at = submitted_at
        self.task_id = task_id
        self.coro = coro

    def __lt__(self, other: "_QueueEntry") -> bool:
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.submitted_at < other.submitted_at


class AsyncScheduler:
    """Priority-aware async task scheduler.

    Tasks are queued with a TaskPriority (1=CRITICAL … 10=BACKGROUND).
    execute_next() dequeues the highest-priority pending task and runs it.
    run_forever() loops until stopped.
    """

    def __init__(self) -> None:
        self._heap: list[_QueueEntry] = []
        self._cancelled: set[str] = set()
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False

    def submit(
        self,
        coro_fn: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        name: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs: Any,
    ) -> str:
        task_id = str(uuid.uuid4())
        entry = _QueueEntry(
            priority=int(priority),
            submitted_at=time.monotonic(),
            task_id=task_id,
            coro=coro_fn(*args, **kwargs),
        )
        # Manual heap push (heapq uses __lt__)
        import heapq

        heapq.heappush(self._heap, entry)
        self._tasks[task_id] = ScheduledTask(
            task_id=task_id,
            name=name or coro_fn.__name__,
            priority=priority,
            submitted_at=entry.submitted_at,
        )
        runtime_events.labels(event_type="scheduler_task_submitted").inc()
        logger.info(
            "scheduler_task_submitted",
            extra={"task_id": task_id, "name": name, "priority": priority},
        )
        return task_id

    def cancel(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        self._cancelled.add(task_id)
        task = self._tasks[task_id]
        if task.status == "pending":
            task.status = "cancelled"
            runtime_events.labels(event_type="scheduler_task_cancelled").inc()
        return True

    async def execute_next(self) -> bool:
        """Dequeue and run the next non-cancelled task. Returns True if one ran."""
        import heapq

        while self._heap:
            entry = heapq.heappop(self._heap)
            if entry.task_id in self._cancelled:
                entry.coro.close()
                continue

            task = self._tasks[entry.task_id]
            task.status = "running"
            try:
                await entry.coro
                task.status = "done"
                runtime_events.labels(event_type="scheduler_task_done").inc()
            except Exception as exc:
                task.status = "failed"
                runtime_events.labels(event_type="scheduler_task_failed").inc()
                logger.warning(
                    "scheduler_task_failed",
                    extra={"task_id": entry.task_id, "error": str(exc)},
                )
            return True
        return False

    async def run_forever(self, poll_interval: float = 0.1) -> None:
        self._running = True
        while self._running:
            ran = await self.execute_next()
            if not ran:
                await asyncio.sleep(poll_interval)

    def stop(self) -> None:
        self._running = False

    def list_tasks(self, status: str | None = None) -> list[ScheduledTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: (t.priority, t.submitted_at))

    @property
    def pending_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == "pending")
