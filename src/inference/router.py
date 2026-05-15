import logging

from src.inference.base_provider import (
    BaseInferenceProvider,
    CompletionRequest,
    CompletionResponse,
)

logger = logging.getLogger(__name__)


class InferenceRouter:
    """Routes inference requests across providers with automatic fallback.

    Providers are tried in order. If the primary fails, the router falls back
    to the next enabled provider and logs a warning. Returns None only when
    every provider fails or none is enabled — callers must handle this case
    and fall back to heuristic cognition.
    """

    def __init__(self, providers: list[BaseInferenceProvider]) -> None:
        self._providers = [p for p in providers if p.enabled]
        if not self._providers:
            logger.warning("inference_router_no_providers_enabled")

    @property
    def enabled(self) -> bool:
        return bool(self._providers)

    @property
    def active_provider(self) -> str:
        return self._providers[0].name if self._providers else "none"

    async def complete(
        self,
        prompt: str,
        system: str = "You are a scientific reasoning assistant.",
        temperature: float = 0.7,
    ) -> str | None:
        request = CompletionRequest(
            prompt=prompt, system=system, temperature=temperature
        )
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                response: CompletionResponse = await provider.complete(request)
                return response.content
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "inference_provider_failed",
                    extra={"provider": provider.name, "error": str(exc)},
                )
        if last_error:
            logger.error(
                "all_inference_providers_failed", extra={"error": str(last_error)}
            )
        return None
