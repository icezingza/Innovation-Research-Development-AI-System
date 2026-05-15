import logging
from typing import Any

logger = logging.getLogger(__name__)


class RuntimeStateManager:
    """Maintains runtime cognitive state, persisted to Redis when available."""

    def __init__(self, store: Any | None = None) -> None:
        self._store = store
        self._local: dict[str, Any] = {"active_agents": [], "cycles": 0}

    async def register_agent(self, agent_id: str) -> None:
        if agent_id not in self._local["active_agents"]:
            self._local["active_agents"].append(agent_id)
        await self._persist("active_agents", self._local["active_agents"])
        logger.info("agent_registered", extra={"agent_id": agent_id})

    async def deregister_agent(self, agent_id: str) -> None:
        agents: list[str] = self._local["active_agents"]
        if agent_id in agents:
            agents.remove(agent_id)
        await self._persist("active_agents", agents)
        logger.info("agent_deregistered", extra={"agent_id": agent_id})

    async def increment_cycle(self) -> int:
        self._local["cycles"] += 1
        await self._persist("cycles", self._local["cycles"])
        return self._local["cycles"]

    async def get_state(self) -> dict[str, Any]:
        if self._store is not None:
            active = await self._store.get_state("active_agents") or []
            cycles = await self._store.get_state("cycles") or 0
            return {"active_agents": active, "cycles": cycles}
        return self._local.copy()

    async def _persist(self, key: str, value: Any) -> None:
        if self._store is not None:
            await self._store.set_state(key, value)
