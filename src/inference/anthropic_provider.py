import logging
from typing import Literal
import httpx
from src.inference.base_provider import (
    BaseInferenceProvider,
    CompletionRequest,
    CompletionResponse,
)

logger = logging.getLogger(__name__)

class AnthropicProvider(BaseInferenceProvider):
    """Anthropic Claude provider optimized with Ephemeral Caching and Thinking Budget."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-7-sonnet-20250219",
        reasoning_tier: Literal["fast", "deep"] = "deep",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._reasoning_tier = reasoning_tier
        self._enabled = bool(api_key)

    @property
    def name(self) -> str:
        return "anthropic-provider"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def reasoning_tier(self) -> Literal["fast", "deep"]:
        return self._reasoning_tier

    @property
    def latency_expectation(self) -> str:
        return "moderate" if self._reasoning_tier == "deep" else "instant"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
            "Content-Type": "application/json",
        }

        messages = [{"role": "user", "content": request.prompt}]

        system_blocks = []
        if request.system:
            system_block = {
                "type": "text",
                "text": request.system,
            }
            if request.enable_caching:
                system_block["cache_control"] = {"type": "ephemeral"}
            system_blocks.append(system_block)

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature if not request.thinking.enabled else 1.0,
        }

        if system_blocks:
            payload["system"] = system_blocks

        if request.thinking.enabled:
            payload["thinking"] = {
                "type": "enabled",
                "budget_tokens": request.thinking.budget_tokens
            }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(
                    "anthropic_api_error",
                    extra={"status_code": response.status_code, "response": response.text},
                )
                raise RuntimeError(f"Anthropic API error {response.status_code}: {response.text}")

            data = response.json()
            
            content_text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content_text += block.get("text", "")

            usage = data.get("usage", {})
            tokens_used = usage.get("output_tokens", 0) + usage.get("input_tokens", 0)
            
            cache_read_tokens = usage.get("cache_read_input_tokens", 0)
            cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)

            return CompletionResponse(
                content=content_text,
                model=self._model,
                provider=self.name,
                tokens_used=tokens_used,
                cached_tokens=cache_read_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_creation_tokens=cache_creation_tokens,
            )
