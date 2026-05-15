import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TraceEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operation: str
    input_hash: str
    output_summary: str
    agent_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_seconds: float = 0.0


class ReasoningTrace:
    """Records reasoning lineage for traceability and replay.

    Writes to three tiers simultaneously:
      - in-memory ring buffer (always, instant access)
      - Redis with 24h TTL (fast distributed access, if available)
      - PostgreSQL reasoning_traces table (permanent audit log, if available)
    """

    def __init__(
        self,
        store: Any | None = None,
        session_factory: Any | None = None,
    ) -> None:
        self._store = store
        self._session_factory = session_factory
        self._local: list[TraceEntry] = []

    @staticmethod
    def hash_input(data: Any) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    async def record(self, entry: TraceEntry) -> None:
        self._local.append(entry)

        # Redis tier
        if self._store is not None:
            try:
                await self._store.set_state(
                    f"trace:{entry.id}", entry.model_dump_json(), ttl_seconds=86400
                )
            except Exception:
                logger.warning("trace_redis_write_failed", extra={"id": entry.id})

        # PostgreSQL tier
        if self._session_factory is not None:
            try:
                from src.memory.schema import ReasoningTraceRecord

                async with self._session_factory() as session:
                    record = ReasoningTraceRecord(
                        id=entry.id,
                        operation=entry.operation,
                        input_hash=entry.input_hash,
                        output_summary=entry.output_summary,
                        agent_id=entry.agent_id,
                        duration_seconds=entry.duration_seconds,
                        timestamp=entry.timestamp,
                    )
                    session.add(record)
                    await session.commit()
            except Exception:
                logger.warning("trace_postgres_write_failed", extra={"id": entry.id})

    async def get_recent(self, limit: int = 100) -> list[TraceEntry]:
        return self._local[-limit:]
