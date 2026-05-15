import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class TraceEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operation: str
    input_hash: str
    output_summary: str
    agent_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_seconds: float = 0.0


class ReasoningTrace:
    """Records reasoning lineage for traceability and replay."""

    def __init__(self, store: Any | None = None) -> None:
        self._store = store
        self._local: list[TraceEntry] = []

    @staticmethod
    def hash_input(data: Any) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    async def record(self, entry: TraceEntry) -> None:
        self._local.append(entry)
        if self._store is not None:
            await self._store.set_state(
                f"trace:{entry.id}", entry.model_dump_json(), ttl_seconds=86400
            )

    async def get_recent(self, limit: int = 100) -> list[TraceEntry]:
        return self._local[-limit:]
