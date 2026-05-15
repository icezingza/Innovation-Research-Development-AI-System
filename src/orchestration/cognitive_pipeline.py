import logging
from typing import Any

from src.governance.policy_enforcer import PolicyDecision, PolicyEnforcer
from src.protocols.agent_message import AgentMessage
from src.telemetry.runtime_metrics import runtime_events
from src.telemetry.tracing import tracer

logger = logging.getLogger(__name__)


class CognitivePipeline:
    """Coordinates agent execution through a governed async pipeline.

    Each agent runs in sequence; its output message is evaluated by the
    PolicyEnforcer before being appended to results. Denied messages are
    dropped and counted — they never propagate downstream.
    """

    def __init__(
        self,
        agents: list[Any],
        policy_enforcer: PolicyEnforcer | None = None,
    ) -> None:
        self._agents = agents
        self._policy = policy_enforcer or PolicyEnforcer()

    async def run(self, context: dict[str, Any]) -> list[AgentMessage]:
        results: list[AgentMessage] = []
        with tracer.start_as_current_span("orchestration.pipeline"):
            for agent in self._agents:
                message = await agent.run(context)
                policy_result = await self._policy.evaluate(message)
                if policy_result.decision == PolicyDecision.ALLOW:
                    results.append(message)
                    runtime_events.labels(event_type="pipeline_step_complete").inc()
                    logger.info(
                        "pipeline_step_complete",
                        extra={"agent_id": agent.agent_id, "message_id": message.id},
                    )
                else:
                    runtime_events.labels(event_type="pipeline_step_denied").inc()
                    logger.warning(
                        "pipeline_step_denied",
                        extra={
                            "agent_id": agent.agent_id,
                            "reason": policy_result.reason,
                        },
                    )
        return results
