import logging

import httpx

from src.inference.base_provider import (
    BaseInferenceProvider,
    CompletionRequest,
    CompletionResponse,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseInferenceProvider):
    """OpenAI-compatible provider: OpenAI, OpenRouter, vLLM, LM Studio."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._enabled = bool(api_key)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    @property
    def name(self) -> str:
        return "openai"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def reasoning_tier(self) -> str:
        # Default to fast, could be deep if using o1 models
        return "fast"

    @property
    def latency_expectation(self) -> str:
        return "moderate"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        client = await self._get_client()
        response = await client.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.prompt},
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()
        return CompletionResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self._model),
            provider=self.name,
            tokens_used=data.get("usage", {}).get("total_tokens"),
        )
