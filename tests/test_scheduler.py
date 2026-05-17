import pytest

from src.runtime.scheduler import AsyncScheduler, TaskPriority


async def _noop() -> None:
    pass


async def _fail() -> None:
    raise RuntimeError("intentional failure")


async def _record(results: list, value: str) -> None:
    results.append(value)


@pytest.mark.asyncio
async def test_scheduler_submit_returns_task_id():
    s = AsyncScheduler()
    task_id = s.submit(_noop, name="test")
    assert isinstance(task_id, str)
    assert len(task_id) == 36


@pytest.mark.asyncio
async def test_scheduler_execute_next_runs_task():
    s = AsyncScheduler()
    results: list[str] = []
    s.submit(_record, results, "hello", name="record", priority=TaskPriority.NORMAL)
    ran = await s.execute_next()
    assert ran is True
    assert results == ["hello"]


@pytest.mark.asyncio
async def test_scheduler_priority_order():
    s = AsyncScheduler()
    results: list[str] = []
    s.submit(_record, results, "low", priority=TaskPriority.LOW)
    s.submit(_record, results, "critical", priority=TaskPriority.CRITICAL)
    s.submit(_record, results, "normal", priority=TaskPriority.NORMAL)

    await s.execute_next()
    await s.execute_next()
    await s.execute_next()

    assert results[0] == "critical"
    assert results[1] == "normal"
    assert results[2] == "low"


@pytest.mark.asyncio
async def test_scheduler_execute_next_empty_returns_false():
    s = AsyncScheduler()
    ran = await s.execute_next()
    assert ran is False


@pytest.mark.asyncio
async def test_scheduler_cancel_skips_task():
    s = AsyncScheduler()
    results: list[str] = []
    task_id = s.submit(_record, results, "should_not_run", priority=TaskPriority.NORMAL)
    s.cancel(task_id)
    await s.execute_next()
    assert results == []


@pytest.mark.asyncio
async def test_scheduler_failed_task_status():
    s = AsyncScheduler()
    task_id = s.submit(_fail, name="failing", priority=TaskPriority.HIGH)
    await s.execute_next()
    tasks = s.list_tasks()
    task = next(t for t in tasks if t.task_id == task_id)
    assert task.status == "failed"


@pytest.mark.asyncio
async def test_scheduler_list_tasks_by_status():
    s = AsyncScheduler()
    s.submit(_noop, name="t1", priority=TaskPriority.NORMAL)
    s.submit(_noop, name="t2", priority=TaskPriority.LOW)
    assert len(s.list_tasks(status="pending")) == 2
    await s.execute_next()
    assert len(s.list_tasks(status="done")) == 1
    assert len(s.list_tasks(status="pending")) == 1


@pytest.mark.asyncio
async def test_scheduler_pending_count():
    s = AsyncScheduler()
    assert s.pending_count == 0
    s.submit(_noop)
    s.submit(_noop)
    assert s.pending_count == 2
    await s.execute_next()
    assert s.pending_count == 1
