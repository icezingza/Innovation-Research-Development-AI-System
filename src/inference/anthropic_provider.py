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

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
# Enables cache_control and extended thinking beta features
_BETA_HEADERS = "prompt-caching-2024-07-31"


class AnthropicProvider(BaseInferenceProvider):
    """Native Anthropic API provider with prompt caching and extended thinking.

    Prompt caching: system block is marked cache_control=ephemeral (5 min TTL).
    First request writes cache (1.25x input cost). Every subsequent request
    with the same system prompt pays 0.1x — up to 90% savings.

    Stack with Batch API for up to 95% total reduction on input tokens.
    """

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
        return "anthropic"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def reasoning_tier(self) -> Literal["fast", "deep"]:
        return self._reasoning_tier

    @property
    def latency_expectation(self) -> Literal["instant", "moderate", "slow"]:
        return "moderate"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload: dict = {
            "model": self._model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
        }

        # System block with cache_control — marks this content for caching.
        # The prefix up to this block is cached after the first request.
        # All agents share the same system prompt → near-100% cache hit rate
        # once the cache is warm (after the first call per 5-min window).
        if request.system:
            payload["system"] = [
                {
                    "type": "text",
                    "text": request.system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        # Extended thinking: only active when thinking_budget > 0
        if request.thinking_budget > 0:
            payload["thinking"] = {
                "type": "enabled",
                "budget_tokens": request.thinking_budget,
            }
            # Extended thinking requires temperature=1
            payload["temperature"] = 1
        else:
            payload["temperature"] = request.temperature

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "anthropic-beta": _BETA_HEADERS,
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(_ANTHROPIC_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens") or 0
        cache_write = usage.get("cache_creation_input_tokens") or 0

        # Emit per-type token metrics for cache hit rate dashboard
        if input_tokens:
            inference_tokens.labels(provider="anthropic", token_type="input").inc(input_tokens)
        if output_tokens:
            inference_tokens.labels(provider="anthropic", token_type="output").inc(output_tokens)
        if cache_read:
            inference_tokens.labels(provider="anthropic", token_type="cached").inc(cache_read)
            logger.info("anthropic_cache_hit", extra={"cache_read_tokens": cache_read})
        if cache_write:
            inference_tokens.labels(provider="anthropic", token_type="cache_write").inc(cache_write)
            logger.debug("anthropic_cache_write", extra={"cache_write_tokens": cache_write})

        # Extract text from content blocks (may include thinking blocks)
        content_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content_text = block["text"]
                break

        return CompletionResponse(
            content=content_text,
            model=data.get("model", self._model),
            provider=self.name,
            tokens_used=input_tokens + output_tokens,
            cached_tokens=cache_read or None,
            cache_write_tokens=cache_write or None,
        )
