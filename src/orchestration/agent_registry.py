import logging
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class CapabilitySpec(BaseModel):
    """Declarative capability metadata for agent discovery."""
    name: str
    version: str = "1.0"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    cost_estimate: Literal["fast", "moderate", "slow"] = "moderate"

class AgentState(BaseModel):
    """Real-time tracking of agent availability and load."""
    status: Literal["idle", "busy", "error"] = "idle"
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    current_load: int = 0

class AgentRegistry:
    """Registry with versioned capabilities and real-time state tracking."""

    def __init__(self) -> None:
        self._agents: dict[str, Any] = {}
        self._capabilities: dict[str, dict[str, CapabilitySpec]] = {} # agent_id -> {cap_name: spec}
        self._states: dict[str, AgentState] = {} # agent_id -> state

    def register(self, agent: Any, capabilities: list[CapabilitySpec] | None = None) -> None:
        agent_id = agent.agent_id
        self._agents[agent_id] = agent
        self._states[agent_id] = AgentState()
        self._capabilities[agent_id] = {cap.name: cap for cap in capabilities} if capabilities else {}
        logger.info("agent_registered", extra={"agent_id": agent_id})

    def update_state(self, agent_id: str, state: AgentState) -> None:
        if agent_id in self._states:
            self._states[agent_id] = state

    def get_state(self, agent_id: str) -> AgentState | None:
        return self._states.get(agent_id)

    def list_ids(self) -> list[str]:
        return list(self._agents.keys())

    def count(self) -> int:
        return len(self._agents)

    def deregister(self, agent_id: str) -> None:
        if agent_id in self._agents:
            del self._agents[agent_id]
            del self._states[agent_id]
            del self._capabilities[agent_id]
            logger.info("agent_deregistered", extra={"agent_id": agent_id})

    def get(self, agent_id: str) -> Any | None:
        return self._agents.get(agent_id)

    def find_by_capability(
        self, 
        capability_name: str, 
        prefer_available: bool = True, 
        min_confidence: float = 0.5
    ) -> list[Any]:
        """Discovery mechanism for AgentCoordinator to find the best candidate."""
        candidates = []
        for a_id, caps in self._capabilities.items():
            if capability_name in caps and caps[capability_name].confidence >= min_confidence:
                if a_id in self._agents:
                    candidates.append((self._agents[a_id], self._states[a_id].current_load))
        
        if prefer_available:
            # Sort by load (ascending) to balance tasks
            candidates.sort(key=lambda x: x[1])
            
        return [c[0] for c in candidates]
