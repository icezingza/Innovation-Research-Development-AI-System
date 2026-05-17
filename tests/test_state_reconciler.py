import asyncio
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import select

from src.memory.schema import Base, MemoryOutboxRecord
from src.memory.research_memory import ResearchMemory, MemoryEntry
from src.memory.state_reconciler import MemoryStateReconciler
from src.infrastructure.event_bus import RuntimeEventBus


@pytest.mark.asyncio
async def test_reconciler_happy_path():
    """Verify standard happy path where memory is stored to outbox and immediately synced."""
    # 1. Setup in-memory SQLite DB
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # 2. Mock external engines
    mock_qdrant = AsyncMock()
    mock_neo4j = AsyncMock()
    event_bus = RuntimeEventBus()

    # 3. Setup research memory with outbox
    memory = ResearchMemory(
        context_engine=mock_qdrant,
        session_factory=session_factory,
        event_bus=event_bus,
    )

    # 4. Instantiate and register the state reconciler
    reconciler = MemoryStateReconciler(
        session_factory=session_factory,
        context_engine=mock_qdrant,
        knowledge_graph=mock_neo4j,
        event_bus=event_bus,
    )
    reconciler.register()

    # 5. Store new entry (triggers outbox save and event publish)
    entry = MemoryEntry(
        topic="Sovereign Outbox Pattern",
        statement="We persist memory to Postgres before publishing to Redis Event Bus.",
        confidence=0.99,
        source="hypothesis_agent",
        session_id="session-test-happy",
        evidence=["architecture_critique"],
    )
    await memory.store(entry)

    # Wait brief moment to let event listener async tasks run
    await asyncio.sleep(0.05)

    # 6. Verify assertions
    mock_qdrant.store_hypothesis.assert_called_once()
    mock_neo4j.store_hypothesis.assert_called_once()

    async with session_factory() as session:
        stmt = select(MemoryOutboxRecord).where(
            MemoryOutboxRecord.entry_id == entry.entry_id
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record is not None
        assert record.status == "synced"
        assert record.retry_count == 0
        assert record.last_error is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_reconciler_retry_and_dlq_recovery():
    """Verify that transient failures trigger retry states, promote to DLQ, and heal upon DLQ retry request."""
    # 1. Setup in-memory SQLite DB
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # 2. Mock external engines (Qdrant fails temporarily)
    mock_qdrant = AsyncMock()
    mock_qdrant.store_hypothesis.side_effect = Exception("Qdrant Connection Timeout")
    mock_neo4j = AsyncMock()
    event_bus = RuntimeEventBus()

    # 3. Setup research memory
    memory = ResearchMemory(
        context_engine=mock_qdrant,
        session_factory=session_factory,
        event_bus=event_bus,
    )

    # 4. Instantiate reconciler with 3 retries max
    reconciler = MemoryStateReconciler(
        session_factory=session_factory,
        context_engine=mock_qdrant,
        knowledge_graph=mock_neo4j,
        event_bus=event_bus,
        max_retries=3,
    )
    reconciler.register()

    # 5. Store memory (triggers event -> Qdrant fails -> outbox marked as 'failed')
    entry = MemoryEntry(
        topic="Sovereign Memory Resilience",
        statement="Outbox retry loops capture temporary network faults.",
        confidence=0.98,
        source="coordination",
        session_id="session-test-dlq",
    )
    await memory.store(entry)

    # Let the initial handler run and fail
    await asyncio.sleep(0.05)

    # Verify status is 'failed' and retry_count is 1
    async with session_factory() as session:
        stmt = select(MemoryOutboxRecord).where(
            MemoryOutboxRecord.entry_id == entry.entry_id
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record is not None
        assert record.status == "failed"
        assert record.retry_count == 1
        assert "Qdrant Connection Timeout" in record.last_error

    # 6. Trigger sweep 1 (retry_count becomes 2)
    await reconciler.reconcile_pending()
    async with session_factory() as session:
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record.status == "failed"
        assert record.retry_count == 2

    # 7. Trigger sweep 2 (retry_count becomes 3 -> Promoted to DLQ)
    await reconciler.reconcile_pending()
    async with session_factory() as session:
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record.status == "dlq"
        assert record.retry_count == 3

    # 8. Healing Qdrant connection!
    mock_qdrant.store_hypothesis.side_effect = None

    # Reconciling pending should NOT run DLQ records
    await reconciler.reconcile_pending()
    async with session_factory() as session:
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record.status == "dlq"

    # 9. Trigger DLQ recovery!
    restored = await reconciler.retry_dlq()
    assert restored == 1

    # Check that outbox is now fully synced!
    async with session_factory() as session:
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record.status == "synced"
        assert record.retry_count == 0
        assert record.last_error is None

    await engine.dispose()
