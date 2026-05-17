import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from src.tenants.context import SYSTEM_TENANT_ID

logger = logging.getLogger(__name__)

_MEMORY_COLLECTION = "research_memory"
_IN_MEMORY_MAX = 2000


class MemoryEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    statement: str
    confidence: float
    source: str  # "workflow", "coordination", "hypothesis_agent", "synthesis_agent"
    session_id: str
    evidence: list[str] = Field(default_factory=list)
    generation: int = 0
    created_at: float = Field(default_factory=time.time)
    tenant_id: str = SYSTEM_TENANT_ID


class ResearchMemory:
    """Cross-session research knowledge store.

    Persists finalized hypotheses and synthesis conclusions across sessions so
    that each new workflow can build on accumulated prior research.

    Three-tier storage (each optional, degrades gracefully):
    - In-memory ring buffer (always available, lost on restart)
    - PostgreSQL via HypothesisRecord (structured, queryable)
    - Qdrant via ContextEngine (semantic similarity search)
    """

    def __init__(
        self,
        context_engine: Any | None = None,
        session_factory: Any | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self._context = context_engine
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._buffer: list[MemoryEntry] = []

    async def store(self, entry: MemoryEntry) -> None:
        # In-memory ring buffer
        self._buffer.append(entry)
        if len(self._buffer) > _IN_MEMORY_MAX:
            self._buffer = self._buffer[-_IN_MEMORY_MAX:]

        # PostgreSQL persistence with Outbox
        if self._session_factory is not None:
            await self._store_postgres(entry)
        else:
            # Fallback to direct synchronous/async sync to Qdrant (for tests or heuristic environments with no DB)
            if self._context is not None:
                await self._store_qdrant(entry)

        logger.info(
            "research_memory_stored",
            extra={
                "entry_id": entry.entry_id,
                "topic": entry.topic[:80],
                "source": entry.source,
            },
        )

    async def recall(self, topic: str, limit: int = 5) -> list[MemoryEntry]:
        """Return semantically relevant prior findings for a topic."""
        if self._context is not None:
            try:
                packet = await self._context.build(topic)
                entries: list[MemoryEntry] = []
                for h in packet.similar_hypotheses[:limit]:
                    entries.append(
                        MemoryEntry(
                            entry_id=str(h.get("id", uuid.uuid4())),
                            topic=topic,
                            statement=h.get("statement", ""),
                            confidence=float(h.get("score", 0.5)),
                            source="qdrant_recall",
                            session_id="",
                        )
                    )
                if entries:
                    return entries
            except Exception as exc:
                logger.warning(
                    "research_memory_qdrant_recall_failed",
                    extra={"error": str(exc)},
                )

        # In-memory fallback: keyword overlap scoring
        topic_words = set(topic.lower().split())
        scored: list[tuple[float, MemoryEntry]] = []
        for entry in self._buffer:
            stmt_words = set(entry.statement.lower().split())
            overlap = len(topic_words & stmt_words)
            if overlap > 0:
                scored.append((overlap / max(len(topic_words), 1), entry))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [e for _, e in scored[:limit]]

    async def get_all(self, limit: int = 100) -> list[MemoryEntry]:
        return list(reversed(self._buffer[-limit:]))

    async def stats(self) -> dict[str, Any]:
        total = len(self._buffer)
        if not self._buffer:
            return {
                "total_entries": 0,
                "avg_confidence": 0.0,
                "sources": {},
                "qdrant_enabled": self._context is not None,
                "postgres_enabled": self._session_factory is not None,
            }
        avg_conf = sum(e.confidence for e in self._buffer) / total
        sources: dict[str, int] = {}
        for e in self._buffer:
            sources[e.source] = sources.get(e.source, 0) + 1
        return {
            "total_entries": total,
            "avg_confidence": round(avg_conf, 4),
            "sources": sources,
            "qdrant_enabled": self._context is not None,
            "postgres_enabled": self._session_factory is not None,
        }

    async def _store_postgres(self, entry: MemoryEntry) -> None:
        from src.memory.schema import HypothesisRecord, MemoryOutboxRecord

        try:
            async with self._session_factory() as session:
                record = HypothesisRecord(
                    id=entry.entry_id,
                    tenant_id=entry.tenant_id,
                    statement=entry.statement,
                    confidence=entry.confidence,
                    topic=entry.topic,
                    source=entry.source,
                    session_id=entry.session_id,
                    evidence=entry.evidence,
                    generation=entry.generation,
                )
                session.add(record)

                outbox = MemoryOutboxRecord(
                    entry_id=entry.entry_id,
                    tenant_id=entry.tenant_id,
                    statement=entry.statement,
                    confidence=entry.confidence,
                    topic=entry.topic,
                    source=entry.source,
                    session_id=entry.session_id,
                    evidence=entry.evidence,
                    generation=entry.generation,
                    status="pending",
                    retry_count=0,
                )
                session.add(outbox)
                await session.commit()

                # Trigger eventual consistency notification via Event Bus if available
                if self._event_bus is not None:
                    from src.infrastructure.event_bus import (
                        RuntimeEvent,
                        TOPIC_MEMORY_STORED,
                    )

                    event = RuntimeEvent(
                        topic=TOPIC_MEMORY_STORED,
                        source_agent_id="research_memory",
                        payload={
                            "entry_id": entry.entry_id,
                            "tenant_id": entry.tenant_id,
                            "topic": entry.topic,
                            "statement": entry.statement,
                        },
                    )
                    await self._event_bus.publish(event)
                    logger.debug(
                        "memory_stored_event_published",
                        extra={"entry_id": entry.entry_id},
                    )

        except Exception as exc:
            logger.error(
                "research_memory_postgres_write_failed",
                extra={"error": str(exc)},
                exc_info=True,
            )

    async def _store_qdrant(self, entry: MemoryEntry) -> None:
        try:
            await self._context.store_hypothesis(
                hypothesis={
                    "statement": entry.statement,
                    "confidence": entry.confidence,
                    "generation": entry.generation,
                    "source": entry.source,
                },
                question=entry.topic,
                task_id=entry.entry_id,
            )
        except Exception as exc:
            logger.warning(
                "research_memory_qdrant_write_failed", extra={"error": str(exc)}
            )
