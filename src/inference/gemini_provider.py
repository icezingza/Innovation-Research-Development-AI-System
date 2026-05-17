import logging
from typing import Literal

import httpx

from src.inference.base_provider import (
    BaseInferenceProvider,
    CompletionRequest,
    CompletionResponse,
)

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
        payload = {
            "contents": [
                {
                    "parts": [{"text": request.prompt}],
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        if request.thinking.enabled:
            payload["generationConfig"]["thinkingConfig"] = {
                "thinkingBudget": request.thinking.budget_tokens
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

            # Extract usage metadata
            usage = data.get("usageMetadata", {})
            tokens_used = usage.get("totalTokenCount")
            cached_tokens = usage.get("cachedContentTokenCount", 0)

            return CompletionResponse(
                content=content,
                model=self._model,
                provider=self.name,
                tokens_used=tokens_used,
                cached_tokens=cached_tokens,
                cache_read_tokens=cached_tokens,
                cache_creation_tokens=0,
            )
