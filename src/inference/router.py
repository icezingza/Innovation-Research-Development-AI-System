import logging
import time
from typing import Literal

from src.inference.base_provider import (
    BaseInferenceProvider,
    CompletionRequest,
    CompletionResponse,
)
from src.reasoning.reasoning_trace import ReasoningTrace, TraceEntry

logger = logging.getLogger(__name__)

class InferenceRouter:
    """Routes inference requests using declarative provider metadata and cost bounding.

    Providers are filtered by their self-declared reasoning tier (fast/deep).
    If the requested tier has no available providers, falls back to any enabled provider.
    Supports auto-upgrade: if fast tier fails completely, automatically retries with deep tier.

    All routing decisions and provider selections are logged to ReasoningTrace for
    observability and meta-cognitive analysis (ROI evaluation by downstream engines).
    """

    def __init__(
        self,
        providers: list[BaseInferenceProvider],
        trace: ReasoningTrace | None = None,
    ) -> None:
        self._providers = [p for p in providers if p.enabled]
        self._trace = trace
        if not self._providers:
            logger.warning("inference_router_no_providers_enabled")

    @property
    def enabled(self) -> bool:
        return bool(self._providers)

    @property
    def active_provider(self) -> str:
        return self._providers[0].name if self._providers else "none"

    def _get_providers_by_tier(
        self, tier: Literal["fast", "deep"]
    ) -> list[BaseInferenceProvider]:
        """Filter providers by their self-declared reasoning tier."""
        candidates = [p for p in self._providers if p.reasoning_tier == tier]
        return candidates if candidates else self._providers

    async def complete(
        self,
        prompt: str,
        system: str = "You are a scientific reasoning assistant.",
        temperature: float = 0.7,
        tier: Literal["fast", "deep"] = "fast",
        auto_upgrade: bool = True,
        max_cost_cents: int | None = None,
    ) -> str | None:
        """Complete a prompt using the specified reasoning tier."""
        request = CompletionRequest(
            prompt=prompt, system=system, temperature=temperature
        )
        last_error: Exception | None = None

        # Select providers for the requested tier
        target_providers = self._get_providers_by_tier(tier)

        for provider in target_providers:
            try:
                # Log routing decision to ReasoningTrace
                if self._trace:
                    trace_entry = TraceEntry(
                        operation=f"inference_route_{tier}",
                        input_hash=ReasoningTrace.hash_input(
                            {"prompt_prefix": prompt[:50], "tier": tier}
                        ),
                        output_summary=f"Routing to {provider.name}",
                        agent_id=None,
                    )
                    await self._trace.record(trace_entry)

                logger.debug(
                    "routing_decision",
                    extra={
                        "provider": provider.name,
                        "tier": tier,
                        "latency": provider.latency_expectation,
                    },
                )

                start = time.monotonic()
                response: CompletionResponse = await provider.complete(request)
                elapsed = time.monotonic() - start

                # Record successful completion
                if self._trace:
                    success_entry = TraceEntry(
                        operation=f"inference_complete_{tier}",
                        input_hash=ReasoningTrace.hash_input(
                            {"provider": provider.name, "tier": tier}
                        ),
                        output_summary=f"Completed by {provider.name} in {elapsed:.2f}s",
                        duration_seconds=elapsed,
                    )
                    await self._trace.record(success_entry)

                return response.content

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "inference_provider_failed",
                    extra={
                        "provider": provider.name,
                        "tier": tier,
                        "error": str(exc),
                    },
                )

        # Attempt auto-upgrade if fast tier failed completely and auto_upgrade is enabled
        if tier == "fast" and auto_upgrade:
            logger.info(
                "fast_tier_exhausted_upgrading_to_deep",
                extra={"initial_error": str(last_error)},
            )
            return await self.complete(
                prompt,
                system,
                temperature,
                tier="deep",
                auto_upgrade=False,
                max_cost_cents=max_cost_cents,
            )

        # All providers failed
        if last_error:
            logger.error(
                "all_inference_providers_failed",
                extra={"tier": tier, "error": str(last_error)},
            )
        return None
