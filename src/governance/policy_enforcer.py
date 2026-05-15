import logging
from enum import Enum

from pydantic import BaseModel

from src.governance.audit_log import AuditEntry, GovernanceAuditLog
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

    def __init__(
        self,
        max_content_bytes: int = 1_000_000,
        audit_log: "GovernanceAuditLog | None" = None,
    ) -> None:
        self._max_content_bytes = max_content_bytes
        self._audit_log = audit_log

    async def _audit(self, message: AgentMessage, result: PolicyResult) -> None:
        if self._audit_log is None:
            return
        entry = AuditEntry(
            decision=result.decision.value,
            reason=result.reason,
            message_id=message.id,
            sender_id=message.sender_id,
            message_type=message.message_type.value,
            content_size_bytes=len(str(message.content).encode()),
        )
        await self._audit_log.record(entry)

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
            await self._audit(message, result)
            return result

        if not message.sender_id:
            result = PolicyResult(
                decision=PolicyDecision.DENY,
                reason="Message missing sender identity",
                message_id=message.id,
            )
            runtime_events.labels(event_type="policy_deny").inc()
            await self._audit(message, result)
            return result

        runtime_events.labels(event_type="policy_allow").inc()
        result = PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="All policy checks passed",
            message_id=message.id,
        )
        await self._audit(message, result)
        return result

    async def enforce(self, message: AgentMessage) -> None:
        result = await self.evaluate(message)
        if result.decision == PolicyDecision.DENY:
            raise PolicyViolationError(result)
