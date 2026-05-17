import logging
from typing import Literal

import httpx

from src.inference.base_provider import (
    BaseInferenceProvider,
    CompletionRequest,
    CompletionResponse,
)
from src.telemetry.runtime_metrics import inference_tokens

logger = logging.getLogger(__name__)

# OpenAI o-series models support reasoning_effort instead of temperature
_O_SERIES_MODELS = {"o1", "o1-mini", "o1-preview", "o3", "o3-mini", "o4-mini"}


class OpenAIProvider(BaseInferenceProvider):
    """OpenAI-compatible provider: OpenAI, OpenRouter, vLLM, LM Studio.

    Prompt caching is automatic for prompts > 1024 tokens — no config needed.
    cached_tokens are logged to Prometheus so you can verify cache hits.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        reasoning_tier: Literal["fast", "deep"] = "fast",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._reasoning_tier = reasoning_tier
        self._enabled = bool(api_key)

    @property
    def name(self) -> str:
        return "openai"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def reasoning_tier(self) -> Literal["fast", "deep"]:
        return self._reasoning_tier

    @property
    def latency_expectation(self) -> Literal["instant", "moderate", "slow"]:
        return "moderate"

    def _is_o_series(self) -> bool:
        return any(self._model.startswith(m) for m in _O_SERIES_MODELS)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            "max_tokens": request.max_tokens,
        }

        if self._is_o_series() and request.thinking_budget > 0:
            # o-series: map thinking_budget to reasoning_effort level
            if request.thinking_budget <= 512:
                payload["reasoning_effort"] = "low"
            elif request.thinking_budget <= 4096:
                payload["reasoning_effort"] = "medium"
            else:
                payload["reasoning_effort"] = "high"
        else:
            payload["temperature"] = request.temperature

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        usage = data.get("usage", {})
        cached = (
            usage.get("prompt_tokens_details", {}).get("cached_tokens") or 0
        )
        total = usage.get("total_tokens")

        # Emit metrics so cache hit rate is visible in Prometheus
        if cached:
            inference_tokens.labels(provider="openai", token_type="cached").inc(cached)
            logger.info("openai_cache_hit", extra={"cached_tokens": cached})
        if total:
            inference_tokens.labels(provider="openai", token_type="input").inc(
                usage.get("prompt_tokens", 0)
            )

        return CompletionResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self._model),
            provider=self.name,
            tokens_used=total,
            cached_tokens=cached or None,
        )
