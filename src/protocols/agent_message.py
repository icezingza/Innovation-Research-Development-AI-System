import uuid
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MessageType(str, Enum):
    PERCEPTION = "perception"
    REASONING = "reasoning"
    ACTION = "action"
    REFLECTION = "reflection"
    COORDINATION = "coordination"
    GOVERNANCE = "governance"


class AgentMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    message_type: MessageType
    content: dict
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None
    trace_id: str | None = None

    model_config = ConfigDict(frozen=True)
