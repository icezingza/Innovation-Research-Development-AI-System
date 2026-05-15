import logging

import httpx

from src.inference.base_provider import (
    BaseInferenceProvider,
    CompletionRequest,
    CompletionResponse,
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseInferenceProvider):
    """Ollama local inference provider."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._reachable: bool | None = None  # None = not yet probed

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def enabled(self) -> bool:
        return self._reachable is not False

    @property
    def reasoning_tier(self) -> str:
        return "fast"

    @property
    def latency_expectation(self) -> str:
        return "moderate"

    async def probe(self) -> bool:
        """Check if the Ollama endpoint is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                self._reachable = response.is_success
        except Exception:
            self._reachable = False
        return bool(self._reachable)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": request.system},
                        {"role": "user", "content": request.prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return CompletionResponse(
                content=data["message"]["content"],
                model=data.get("model", self._model),
                provider=self.name,
            )
