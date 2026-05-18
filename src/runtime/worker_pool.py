import asyncio
import logging

from src.runtime.scheduler import AsyncScheduler
from src.telemetry.runtime_metrics import runtime_events

logger = logging.getLogger(__name__)


class AsyncWorkerPool:
    """Bounded concurrency pool that drains tasks from AsyncScheduler.

    Spawns `max_workers` concurrent asyncio tasks, each pulling work from
    the scheduler. Workers self-idle when the queue is empty and wake up
    automatically when new tasks arrive (via poll_interval).

    Usage:
        pool = AsyncWorkerPool(scheduler=scheduler, max_workers=4)
        await pool.start()
        ...
        await pool.stop()
    """

    def __init__(
        self,
        scheduler: AsyncScheduler,
        max_workers: int = 4,
        poll_interval: float = 0.05,
    ) -> None:
        self._scheduler = scheduler
        self._max_workers = max_workers
        self._poll_interval = poll_interval
        self._workers: list[asyncio.Task] = []
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    @property
    def worker_count(self) -> int:
        return len([w for w in self._workers if not w.done()])

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(
                self._worker_loop(worker_id=i),
                name=f"worker-{i}",
            )
            for i in range(self._max_workers)
        ]
        runtime_events.labels(event_type="worker_pool_started").inc()
        logger.info("worker_pool_started", extra={"max_workers": self._max_workers})

    async def stop(self) -> None:
        self._running = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []
        runtime_events.labels(event_type="worker_pool_stopped").inc()
        logger.info("worker_pool_stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        logger.debug("worker_started", extra={"worker_id": worker_id})
        while self._running:
            try:
                ran = await self._scheduler.execute_next()
                if not ran:
                    await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(
                    "worker_loop_error",
                    extra={"worker_id": worker_id, "error": str(exc)},
                )
        logger.debug("worker_stopped", extra={"worker_id": worker_id})
