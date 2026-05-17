from typing import Literal

import pytest

from src.inference.base_provider import (
    BaseInferenceProvider,
    CompletionRequest,
    CompletionResponse,
)
from src.inference.router import InferenceRouter


class CloseTrackingProvider(BaseInferenceProvider):
    def __init__(self) -> None:
        self.closed = False

    @property
    def name(self) -> str:
        return "close-tracking"

    @property
    def enabled(self) -> bool:
        return True

    @property
    def reasoning_tier(self) -> Literal["fast", "deep"]:
        return "fast"

    @property
    def latency_expectation(self) -> Literal["instant", "moderate", "slow"]:
        return "instant"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            content=request.prompt,
            model="test",
            provider=self.name,
        )

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_inference_router_closes_enabled_providers() -> None:
    provider = CloseTrackingProvider()
    router = InferenceRouter([provider])

    await router.close()

    assert provider.closed is True
