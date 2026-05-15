from abc import ABC, abstractmethod
from typing import Literal
from pydantic import BaseModel

class CompletionRequest(BaseModel):
    prompt: str
    system: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048

class CompletionResponse(BaseModel):
    content: str
    model: str
    provider: str
    tokens_used: int | None = None

class BaseInferenceProvider(ABC):
    """Contract that all inference providers must satisfy.

    Providers declare their reasoning capability (fast vs. deep) and latency
    expectations to enable intelligent routing and cost-aware tiering.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider identifier."""
        ...

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether this provider is available for inference."""
        ...

    @property
    @abstractmethod
    def reasoning_tier(self) -> Literal["fast", "deep"]:
        """Provider's native reasoning capability.

        - 'fast': optimized for speed (e.g., ollama, gpt-4o-mini, claude-haiku)
        - 'deep': designed for complex reasoning (e.g., o1, claude-opus)
        """
        return "fast"

    @property
    @abstractmethod
    def latency_expectation(self) -> Literal["instant", "moderate", "slow"]:
        """Expected response latency for cost/performance trade-off."""
        return "moderate"

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute inference request and return completion."""
        ...
