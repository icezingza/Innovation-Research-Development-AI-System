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


class GeminiProvider(BaseInferenceProvider):
    """Google Gemini AI provider."""

    def __init__(
        self,
        api_key: str,
        model: str,
        reasoning_tier: Literal["fast", "deep"] = "fast",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._reasoning_tier = reasoning_tier
        self._enabled = bool(api_key)

    @property
    def name(self) -> str:
        return "gemini-provider"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def reasoning_tier(self) -> Literal["fast", "deep"]:
        return self._reasoning_tier

    @property
    def latency_expectation(self) -> Literal["instant", "moderate", "slow"]:
        return "instant"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        )

        # Build payload according to Gemini API spec
        generation_config: dict = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
        }

        # Thinking budget: 0 = disabled, >0 = max thinking tokens (Gemini 2.5+)
        if request.thinking_budget > 0:
            generation_config["thinkingConfig"] = {
                "thinkingBudget": request.thinking_budget
            }

        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": generation_config,
        }

        # Add system instruction if provided
        if request.system:
            payload["system_instruction"] = {
                "parts": [{"text": request.system}]
            }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self._api_key
                },
                json=payload,
            )
            
            if response.status_code != 200:
                logger.error(
                    "gemini_api_error",
                    extra={
                        "status_code": response.status_code,
                        "response": response.text,
                    },
                )
                # Avoid printing the full URL in the exception as it might contain the key if we used query params
                raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")

            data = response.json()
            
            # Extract content from candidates
            try:
                content = data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                logger.error(
                    "gemini_response_parsing_error",
                    extra={"error": str(e), "data": data},
                )
                raise ValueError("Failed to parse Gemini response") from e

            usage = data.get("usageMetadata", {})
            tokens_used = usage.get("totalTokenCount")
            # cachedContentTokenCount is present when implicit context caching hits
            cached = usage.get("cachedContentTokenCount") or 0

            if cached:
                inference_tokens.labels(provider="gemini", token_type="cached").inc(cached)
                logger.info("gemini_cache_hit", extra={"cached_tokens": cached})
            if tokens_used:
                inference_tokens.labels(provider="gemini", token_type="input").inc(
                    usage.get("promptTokenCount", 0)
                )

            return CompletionResponse(
                content=content,
                model=self._model,
                provider=self.name,
                tokens_used=tokens_used,
                cached_tokens=cached or None,
            )
