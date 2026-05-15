import json
import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_AUDIT_REDIS_KEY = "governance:audit"
_AUDIT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
_MAX_IN_MEMORY = 1000


class AuditEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    decision: str
    reason: str
    message_id: str
    sender_id: str
    message_type: str
    content_size_bytes: int
    extra: dict[str, Any] = Field(default_factory=dict)


class GovernanceAuditLog:
    """Append-only audit trail for every governance decision.

    Writes to an in-memory ring buffer (newest-1000) and, when a Redis
    store is wired, also persists to a Redis list with a 7-day TTL.
    """

    def __init__(self, redis_store: Any | None = None) -> None:
        self._redis = redis_store
        self._buffer: list[AuditEntry] = []

    async def record(self, entry: AuditEntry) -> None:
        self._buffer.append(entry)
        if len(self._buffer) > _MAX_IN_MEMORY:
            self._buffer = self._buffer[-_MAX_IN_MEMORY:]

        if self._redis is not None:
            try:
                payload = entry.model_dump_json()
                await self._redis._client.lpush(_AUDIT_REDIS_KEY, payload)
                await self._redis._client.expire(_AUDIT_REDIS_KEY, _AUDIT_TTL_SECONDS)
            except Exception as exc:
                logger.warning(
                    "audit_redis_write_failed", extra={"error": str(exc)}
                )

        logger.info(
            "governance_audit",
            extra={
                "entry_id": entry.entry_id,
                "decision": entry.decision,
                "message_id": entry.message_id,
                "sender_id": entry.sender_id,
            },
        )

    async def get_recent(self, limit: int = 100) -> list[AuditEntry]:
        if self._redis is not None:
            try:
                raw = await self._redis._client.lrange(
                    _AUDIT_REDIS_KEY, 0, limit - 1
                )
                entries: list[AuditEntry] = []
                for item in raw:
                    try:
                        data = json.loads(item)
                        entries.append(AuditEntry(**data))
                    except Exception:
                        continue
                return entries
            except Exception as exc:
                logger.warning(
                    "audit_redis_read_failed", extra={"error": str(exc)}
                )

        return list(reversed(self._buffer[-limit:]))
