import asyncio

import pytest

from src.runtime.scheduler import AsyncScheduler, TaskPriority
from src.runtime.worker_pool import AsyncWorkerPool


@pytest.mark.asyncio
async def test_worker_pool_starts_and_stops():
    scheduler = AsyncScheduler()
    pool = AsyncWorkerPool(scheduler=scheduler, max_workers=2)
    await pool.start()
    assert pool.running is True
    await pool.stop()
    assert pool.running is False


@pytest.mark.asyncio
async def test_worker_pool_executes_tasks():
    scheduler = AsyncScheduler()
    pool = AsyncWorkerPool(scheduler=scheduler, max_workers=2, poll_interval=0.01)
    results: list[int] = []

    async def task(value: int) -> None:
        results.append(value)

    await pool.start()
    scheduler.submit(task, 1, priority=TaskPriority.NORMAL)
    scheduler.submit(task, 2, priority=TaskPriority.NORMAL)
    scheduler.submit(task, 3, priority=TaskPriority.NORMAL)

    # Give workers time to drain
    await asyncio.sleep(0.15)
    await pool.stop()
    assert sorted(results) == [1, 2, 3]


@pytest.mark.asyncio
async def test_worker_pool_concurrent_execution():
    scheduler = AsyncScheduler()
    pool = AsyncWorkerPool(scheduler=scheduler, max_workers=3, poll_interval=0.01)
    concurrent_peak = [0]
    active = [0]

    async def slow_task() -> None:
        active[0] += 1
        concurrent_peak[0] = max(concurrent_peak[0], active[0])
        await asyncio.sleep(0.05)
        active[0] -= 1

    await pool.start()
    for _ in range(3):
        scheduler.submit(slow_task, priority=TaskPriority.NORMAL)

    await asyncio.sleep(0.2)
    await pool.stop()
    assert concurrent_peak[0] >= 2  # At least 2 ran concurrently


@pytest.mark.asyncio
async def test_worker_pool_handles_failing_tasks():
    scheduler = AsyncScheduler()
    pool = AsyncWorkerPool(scheduler=scheduler, max_workers=1, poll_interval=0.01)

    async def failing_task() -> None:
        raise RuntimeError("intentional failure")

    async def good_task(results: list) -> None:
        results.append("ok")

    results: list[str] = []
    await pool.start()
    scheduler.submit(failing_task, priority=TaskPriority.HIGH)
    scheduler.submit(good_task, results, priority=TaskPriority.NORMAL)

    await asyncio.sleep(0.2)
    await pool.stop()
    assert results == ["ok"]


@pytest.mark.asyncio
async def test_worker_pool_stop_is_idempotent():
    scheduler = AsyncScheduler()
    pool = AsyncWorkerPool(scheduler=scheduler, max_workers=2)
    await pool.start()
    await pool.stop()
    await pool.stop()  # should not raise
    assert pool.running is False
