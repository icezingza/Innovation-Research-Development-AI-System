import asyncio
import logging
from typing import Any
from datetime import UTC, datetime

from sqlalchemy import select

from src.infrastructure.event_bus import (
    RuntimeEventBus,
    RuntimeEvent,
    TOPIC_MEMORY_STORED,
)
from src.memory.schema import MemoryOutboxRecord

logger = logging.getLogger(__name__)


class MemoryStateReconciler:
    """State reconciler that processes memory outbox records asynchronously.

    Guarantees eventually consistent synchronization of postgres memory (HypothesisRecord)
    to semantic stores (Qdrant via ContextEngine) and reasoning graphs (Neo4j via KnowledgeGraph).

    Handles temporary service downtime with automatic retries and dead-letter queue (DLQ) containment.
    """

    def __init__(
        self,
        session_factory: Any,
        context_engine: Any | None = None,
        knowledge_graph: Any | None = None,
        event_bus: RuntimeEventBus | None = None,
        max_retries: int = 5,
    ) -> None:
        self._session_factory = session_factory
        self._context = context_engine
        self._knowledge_graph = knowledge_graph
        self._event_bus = event_bus
        self._max_retries = max_retries
        self._background_task: asyncio.Task | None = None
        self._is_running = False

    def register(self) -> None:
        """Register subscriber to the event bus for immediate real-time sync."""
        if self._event_bus is not None:
            self._event_bus.subscribe(TOPIC_MEMORY_STORED, self.on_memory_stored)
            logger.info("memory_state_reconciler_registered_to_event_bus")

    async def start(self, interval_seconds: float = 30.0) -> None:
        """Start the background synchronization sweep loop."""
        if self._is_running:
            return
        self._is_running = True
        self.register()
        self._background_task = asyncio.create_task(
            self._background_sweep_loop(interval_seconds)
        )
        logger.info(
            "memory_state_reconciler_background_loop_started",
            extra={"interval_seconds": interval_seconds},
        )

    async def stop(self) -> None:
        """Stop the background loop cleanly."""
        self._is_running = False
        if self._background_task is not None:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
        logger.info("memory_state_reconciler_background_loop_stopped")

    async def on_memory_stored(self, event: RuntimeEvent) -> None:
        """Reaction handler to TOPIC_MEMORY_STORED for low-latency synchronization."""
        entry_id = event.payload.get("entry_id")
        if not entry_id:
            return

        logger.debug(
            "reconciler_immediate_sync_triggered", extra={"entry_id": entry_id}
        )
        # Spin up a concurrent task to run the sync for low-latency response on event loop
        asyncio.create_task(self.sync_outbox_by_entry_id(entry_id))

    async def sync_outbox_by_entry_id(self, entry_id: str) -> bool:
        """Sync a specific outbox record by its entry_id."""
        try:
            async with self._session_factory() as session:
                stmt = select(MemoryOutboxRecord).where(
                    MemoryOutboxRecord.entry_id == entry_id,
                    MemoryOutboxRecord.status.in_(["pending", "failed"]),
                )
                res = await session.execute(stmt)
                record = res.scalar_one_or_none()
                if not record:
                    return False

                return await self._sync_single_record(session, record)
        except Exception as exc:
            logger.warning(
                "reconciler_immediate_sync_failed",
                extra={"entry_id": entry_id, "error": str(exc)},
            )
            return False

    async def reconcile_pending(self) -> int:
        """Scans the Postgres outbox queue for pending or failed records and attempts sync.

        Returns:
            The number of successfully synchronized records in this run.
        """
        success_count = 0
        try:
            async with self._session_factory() as session:
                stmt = (
                    select(MemoryOutboxRecord)
                    .where(MemoryOutboxRecord.status.in_(["pending", "failed"]))
                    .order_by(MemoryOutboxRecord.created_at.asc())
                )
                res = await session.execute(stmt)
                records = res.scalars().all()

                if not records:
                    return 0

                logger.info(
                    "reconciler_found_pending_records", extra={"count": len(records)}
                )
                for record in records:
                    success = await self._sync_single_record(session, record)
                    if success:
                        success_count += 1
        except Exception as exc:
            logger.error(
                "reconciler_sweep_failed", extra={"error": str(exc)}, exc_info=True
            )

        return success_count

    async def retry_dlq(self) -> int:
        """Resets all Dead-Letter Queue ('dlq') entries to 'pending' state and retries them."""
        reset_count = 0
        try:
            async with self._session_factory() as session:
                stmt = select(MemoryOutboxRecord).where(
                    MemoryOutboxRecord.status == "dlq"
                )
                res = await session.execute(stmt)
                records = res.scalars().all()

                if not records:
                    logger.info("reconciler_retry_dlq_no_records_found")
                    return 0

                for record in records:
                    record.status = "pending"
                    record.retry_count = 0
                    record.last_error = None
                    reset_count += 1

                await session.commit()
                logger.info(
                    "reconciler_dlq_reset_success", extra={"count": reset_count}
                )
        except Exception as exc:
            logger.error(
                "reconciler_dlq_reset_failed", extra={"error": str(exc)}, exc_info=True
            )
            return 0

        # Trigger immediate reconciliation run
        await self.reconcile_pending()
        return reset_count

    async def _sync_single_record(
        self, session: Any, record: MemoryOutboxRecord
    ) -> bool:
        """Attempts to sync one record to semantic vector search and graph databases.

        Increments retry count on failure. Promotes to 'dlq' status if retries exceed ceiling.
        """
        logger.info(
            "reconciler_syncing_record",
            extra={"entry_id": record.entry_id, "topic": record.topic[:60]},
        )
        errors = []

        # 1. Sync to Qdrant Context Engine
        if self._context is not None:
            try:
                await self._context.store_hypothesis(
                    hypothesis={
                        "statement": record.statement,
                        "confidence": record.confidence,
                        "generation": record.generation,
                        "source": record.source,
                    },
                    question=record.topic,
                    task_id=record.entry_id,
                )
                logger.debug(
                    "reconciler_qdrant_sync_ok", extra={"entry_id": record.entry_id}
                )
            except Exception as exc:
                errors.append(f"QdrantError: {str(exc)}")
                logger.warning(
                    "reconciler_qdrant_sync_failed",
                    extra={"entry_id": record.entry_id, "error": str(exc)},
                )

        # 2. Sync to Neo4j Knowledge Graph
        if self._knowledge_graph is not None:
            try:
                # We map session_id as the task reasoning thread reference in Neo4j
                await self._knowledge_graph.store_hypothesis(
                    hypothesis_id=record.entry_id,
                    statement=record.statement,
                    confidence=record.confidence,
                    generation=record.generation,
                    task_id=record.session_id,
                )
                logger.debug(
                    "reconciler_neo4j_sync_ok", extra={"entry_id": record.entry_id}
                )
            except Exception as exc:
                errors.append(f"Neo4jError: {str(exc)}")
                logger.warning(
                    "reconciler_neo4j_sync_failed",
                    extra={"entry_id": record.entry_id, "error": str(exc)},
                )

        # 3. Handle status updates and database commits
        try:
            if not errors:
                record.status = "synced"
                record.last_error = None
                record.updated_at = datetime.now(UTC)
                await session.commit()
                logger.info(
                    "reconciler_record_sync_success",
                    extra={"entry_id": record.entry_id},
                )
                return True
            else:
                record.retry_count += 1
                record.last_error = " | ".join(errors)
                record.updated_at = datetime.now(UTC)

                if record.retry_count >= self._max_retries:
                    record.status = "dlq"
                    logger.error(
                        "reconciler_record_promoted_to_dlq",
                        extra={
                            "entry_id": record.entry_id,
                            "retries": record.retry_count,
                            "last_error": record.last_error,
                        },
                    )
                else:
                    record.status = "failed"
                    logger.warning(
                        "reconciler_record_sync_failed_marked_for_retry",
                        extra={
                            "entry_id": record.entry_id,
                            "retries": record.retry_count,
                            "last_error": record.last_error,
                        },
                    )
                await session.commit()
                return False
        except Exception as db_exc:
            logger.error(
                "reconciler_failed_to_commit_sync_state",
                extra={"entry_id": record.entry_id, "error": str(db_exc)},
            )
            return False

    async def _background_sweep_loop(self, interval_seconds: float) -> None:
        """Background infinite loop to periodically reconcile any missed/failed memory logs."""
        while self._is_running:
            try:
                await asyncio.sleep(interval_seconds)
                if self._is_running:
                    await self.reconcile_pending()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(
                    "reconciler_background_loop_error", extra={"error": str(exc)}
                )
