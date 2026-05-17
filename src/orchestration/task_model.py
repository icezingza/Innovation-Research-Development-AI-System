from typing import Any, Literal
from pydantic import BaseModel


class TaskRequest(BaseModel):
    """Structured request for agentic delegation."""

    task_id: str
    required_capability: str
    payload: dict[str, Any]
    priority: Literal["low", "medium", "high"] = "medium"
    min_confidence: float = 0.5


class TaskResult(BaseModel):
    """Result of an agent's execution of a task."""

    task_id: str
    agent_id: str
    success: bool
    output: Any
    duration_seconds: float
    error_message: str | None = None
