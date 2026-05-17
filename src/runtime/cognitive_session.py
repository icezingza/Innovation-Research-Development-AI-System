"""Cognitive session management with persistent state across interactions.

Sessions track active research goals, workflow execution history, and
accumulated findings. Backed by Redis when available; falls back to
in-memory storage for single-process deployments.
"""

import json
import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_SESSION_TTL_SECONDS = 86_400  # 24 h
_MAX_IN_MEMORY_SESSIONS = 512
_KEY_PREFIX = "cognitive:session:"


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    goals: list[str] = Field(default_factory=list)
    workflow_ids: list[str] = Field(default_factory=list)
    findings_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class CognitiveSessionManager:
    """Manages the full lifecycle of cognitive sessions.

    Redis storage: JSON serialized under ``cognitive:session:<id>`` with TTL.
    In-memory fallback: LRU-like dict capped at _MAX_IN_MEMORY_SESSIONS.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._memory: dict[str, SessionState] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, metadata: dict[str, Any] | None = None) -> SessionState:
        session = SessionState(metadata=metadata or {})
        await self._save(session)
        logger.info("session_created", extra={"session_id": session.session_id})
        return session

    async def get(self, session_id: str) -> SessionState | None:
        if self._redis is not None:
            try:
                raw = await self._redis.get(f"{_KEY_PREFIX}{session_id}")
                if raw:
                    return SessionState(**json.loads(raw))
            except Exception as exc:
                logger.warning("session_redis_get_error", extra={"error": str(exc)})
        return self._memory.get(session_id)

    async def update(self, session: SessionState) -> None:
        session.updated_at = time.time()
        await self._save(session)

    async def close(self, session_id: str) -> bool:
        session = await self.get(session_id)
        if session is None:
            return False
        session.active = False
        await self.update(session)
        logger.info("session_closed", extra={"session_id": session_id})
        return True

    async def delete(self, session_id: str) -> bool:
        deleted = False
        if self._redis is not None:
            try:
                result = await self._redis.delete(f"{_KEY_PREFIX}{session_id}")
                deleted = result > 0
            except Exception as exc:
                logger.warning("session_redis_delete_error", extra={"error": str(exc)})
        if session_id in self._memory:
            del self._memory[session_id]
            deleted = True
        return deleted

    # ------------------------------------------------------------------
    # Session enrichment helpers
    # ------------------------------------------------------------------

    async def add_goal(self, session_id: str, goal: str) -> bool:
        session = await self.get(session_id)
        if session is None:
            return False
        if goal not in session.goals:
            session.goals.append(goal)
        await self.update(session)
        return True

    async def record_workflow(self, session_id: str, workflow_id: str) -> bool:
        session = await self.get(session_id)
        if session is None:
            return False
        if workflow_id not in session.workflow_ids:
            session.workflow_ids.append(workflow_id)
        await self.update(session)
        return True

    async def increment_findings(self, session_id: str, count: int = 1) -> bool:
        session = await self.get(session_id)
        if session is None:
            return False
        session.findings_count += count
        await self.update(session)
        return True

    async def list_active(self, limit: int = 50) -> list[SessionState]:
        """Return active sessions from in-memory store (best-effort)."""
        sessions = list(self._memory.values())
        active = [s for s in sessions if s.active]
        active.sort(key=lambda s: s.updated_at, reverse=True)
        return active[:limit]

    async def stats(self) -> dict[str, Any]:
        all_sessions = list(self._memory.values())
        active_count = sum(1 for s in all_sessions if s.active)
        return {
            "total_in_memory": len(all_sessions),
            "active": active_count,
            "redis_backed": self._redis is not None,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _save(self, session: SessionState) -> None:
        if self._redis is not None:
            try:
                await self._redis.setex(
                    f"{_KEY_PREFIX}{session.session_id}",
                    _SESSION_TTL_SECONDS,
                    session.model_dump_json(),
                )
            except Exception as exc:
                logger.warning("session_redis_save_error", extra={"error": str(exc)})

        # Always keep in-memory copy
        if len(self._memory) >= _MAX_IN_MEMORY_SESSIONS:
            # Evict oldest
            oldest = min(self._memory.values(), key=lambda s: s.updated_at)
            del self._memory[oldest.session_id]
        self._memory[session.session_id] = session
