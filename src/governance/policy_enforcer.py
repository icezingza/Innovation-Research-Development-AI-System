import logging
from enum import Enum

from pydantic import BaseModel

from src.protocols.agent_message import AgentMessage
from src.telemetry.runtime_metrics import runtime_events

logger = logging.getLogger(__name__)


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


class PolicyResult(BaseModel):
    decision: PolicyDecision
    reason: str
    message_id: str


class PolicyViolationError(Exception):
    def __init__(self, result: PolicyResult) -> None:
        super().__init__(f"Policy denied [{result.message_id}]: {result.reason}")
        self.result = result


class PolicyEnforcer:
    """Runtime governance layer — every agent action passes through here."""

    def __init__(self, max_content_bytes: int = 1_000_000) -> None:
        self._max_content_bytes = max_content_bytes

    async def evaluate(self, message: AgentMessage) -> PolicyResult:
        content_size = len(str(message.content).encode())
        if content_size > self._max_content_bytes:
            limit = self._max_content_bytes
            result = PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Content size {content_size} exceeds limit {limit}",
                message_id=message.id,
            )
            logger.warning(
                "policy_deny",
                extra={"message_id": message.id, "reason": result.reason},
            )
            runtime_events.labels(event_type="policy_deny").inc()
            return result

        if not message.sender_id:
            result = PolicyResult(
                decision=PolicyDecision.DENY,
                reason="Message missing sender identity",
                message_id=message.id,
            )
            runtime_events.labels(event_type="policy_deny").inc()
            return result

        runtime_events.labels(event_type="policy_allow").inc()
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="All policy checks passed",
            message_id=message.id,
        )

    async def enforce(self, message: AgentMessage) -> None:
        result = await self.evaluate(message)
        if result.decision == PolicyDecision.DENY:
            raise PolicyViolationError(result)
