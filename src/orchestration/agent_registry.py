import logging
from typing import Any

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central registry for cognitive agent discovery and lifecycle tracking."""

    def __init__(self) -> None:
        self._agents: dict[str, Any] = {}

    def register(self, agent: Any) -> None:
        self._agents[agent.agent_id] = agent
        logger.info("agent_registered", extra={"agent_id": agent.agent_id})

    def deregister(self, agent_id: str) -> None:
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info("agent_deregistered", extra={"agent_id": agent_id})

    def get(self, agent_id: str) -> Any | None:
        return self._agents.get(agent_id)

    def list_ids(self) -> list[str]:
        return list(self._agents.keys())

    def count(self) -> int:
        return len(self._agents)
