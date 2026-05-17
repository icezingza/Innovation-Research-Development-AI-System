"""Dynamic agent spawning for runtime cognitive scaling.

AgentSpawner creates specialized agents on demand and can scale an
AgentCoordinator by injecting new HypothesisAgent or CritiqueAgent
instances without restart.
"""

import logging
import uuid
from typing import Any

from src.agents.critique_agent import CritiqueAgent
from src.agents.hypothesis_agent import HypothesisAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.infrastructure.event_bus import RuntimeEventBus

logger = logging.getLogger(__name__)

_KNOWN_AGENT_TYPES = {"hypothesis", "critique", "synthesis"}


class SpawnRecord:
    def __init__(self, agent_id: str, agent_type: str, agent: Any) -> None:
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.agent = agent


class AgentSpawner:
    """Creates and tracks specialized cognitive agents at runtime.

    Agents are keyed by a generated agent_id. The spawner also supports
    scale_coordinator() which injects additional hypothesis/critique agents
    into a live AgentCoordinator instance.
    """

    def __init__(
        self,
        event_bus: RuntimeEventBus,
        inference_router: Any | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._inference_router = inference_router
        self._registry: dict[str, SpawnRecord] = {}

    def spawn(self, agent_type: str, **kwargs: Any) -> SpawnRecord:
        """Instantiate a new agent of the given type and register it.

        Supported types: 'hypothesis', 'critique', 'synthesis'.
        """
        if agent_type not in _KNOWN_AGENT_TYPES:
            raise ValueError(
                f"Unknown agent type '{agent_type}'. "
                f"Supported: {sorted(_KNOWN_AGENT_TYPES)}"
            )
        agent_id = f"{agent_type}:{uuid.uuid4().hex[:8]}"
        _inf = self._inference_router

        if agent_type == "hypothesis":
            agent = HypothesisAgent(
                inference_router=_inf,
                event_bus=self._event_bus,
                **kwargs,
            )
        elif agent_type == "critique":
            agent = CritiqueAgent(
                inference_router=_inf,
                event_bus=self._event_bus,
                **kwargs,
            )
        else:
            agent = SynthesisAgent(
                inference_router=_inf,
                event_bus=self._event_bus,
                **kwargs,
            )

        record = SpawnRecord(agent_id=agent_id, agent_type=agent_type, agent=agent)
        self._registry[agent_id] = record
        logger.info("agent_spawned", extra={"agent_id": agent_id, "type": agent_type})
        return record

    def scale_coordinator(self, coordinator: Any, agent_type: str) -> SpawnRecord:
        """Spawn an agent and inject it into an existing AgentCoordinator.

        coordinator must expose .hypothesis_agents or .critique_agents lists.
        """
        record = self.spawn(agent_type)
        if agent_type == "hypothesis":
            coordinator.hypothesis_agents.append(record.agent)
        elif agent_type == "critique":
            coordinator.critique_agents.append(record.agent)
        else:
            # Synthesis: swap the singleton
            coordinator.synthesis_agent = record.agent
        logger.info(
            "coordinator_scaled",
            extra={"agent_id": record.agent_id, "type": agent_type},
        )
        return record

    def terminate(self, agent_id: str) -> bool:
        if agent_id not in self._registry:
            return False
        del self._registry[agent_id]
        logger.info("agent_terminated", extra={"agent_id": agent_id})
        return True

    def list_agents(self) -> list[dict[str, str]]:
        return [
            {"agent_id": r.agent_id, "agent_type": r.agent_type}
            for r in self._registry.values()
        ]

    def stats(self) -> dict[str, Any]:
        types: dict[str, int] = {}
        for record in self._registry.values():
            types[record.agent_type] = types.get(record.agent_type, 0) + 1
        return {"total_spawned": len(self._registry), "by_type": types}
