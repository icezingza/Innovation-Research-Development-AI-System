import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any

from src.protocols.agent_message import AgentMessage, MessageType
from src.telemetry.runtime_metrics import active_agents, runtime_events
from src.telemetry.tracing import tracer

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for all cognitive agents.

    Subclasses implement perceive/reason/act. The run() lifecycle wraps them
    with telemetry, tracing, and structured logging so orchestration layers
    get consistent observability without boilerplate in each agent.
    """

    def __init__(self, agent_id: str | None = None) -> None:
        self.agent_id = agent_id or str(uuid.uuid4())
        self._active = False

    async def run(self, context: dict[str, Any]) -> AgentMessage:
        self._active = True
        active_agents.inc()
        runtime_events.labels(event_type="agent_cycle_start").inc()
        logger.info(
            "agent_cycle_start",
            extra={"agent_id": self.agent_id, "context_keys": list(context.keys())},
        )
        try:
            with tracer.start_as_current_span(f"agent.{self.agent_id}.cycle"):
                perception = await self.perceive(context)
                reasoning = await self.reason(perception)
                action = await self.act(reasoning)
            runtime_events.labels(event_type="agent_cycle_complete").inc()
            return AgentMessage(
                sender_id=self.agent_id,
                message_type=MessageType.ACTION,
                content={"action": action, "reasoning": reasoning},
            )
        except Exception:
            runtime_events.labels(event_type="agent_cycle_error").inc()
            logger.exception("agent_cycle_error", extra={"agent_id": self.agent_id})
            raise
        finally:
            self._active = False
            active_agents.dec()

    @abstractmethod
    async def perceive(self, context: dict[str, Any]) -> dict[str, Any]:
        """Transform raw context into structured perception."""
        ...

    @abstractmethod
    async def reason(self, perception: dict[str, Any]) -> dict[str, Any]:
        """Produce structured reasoning from perception."""
        ...

    @abstractmethod
    async def act(self, reasoning: dict[str, Any]) -> dict[str, Any]:
        """Decide and produce an action from reasoning output."""
        ...
