from abc import ABC, abstractmethod

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
    """Contract that all inference providers must satisfy."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def enabled(self) -> bool: ...

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse: ...
