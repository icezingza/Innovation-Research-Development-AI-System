"""Tests for the provider-agnostic inference layer."""

import pytest

from src.inference.base_provider import CompletionRequest, CompletionResponse
from src.inference.embedding_provider import DisabledEmbeddingProvider
from src.inference.router import InferenceRouter


class _FakeProvider:
    """Test double for BaseInferenceProvider."""

    def __init__(self, name: str, enabled: bool, response: str | None = None) -> None:
        self._name = name
        self._enabled = enabled
        self._response = response
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.calls += 1
        if self._response is None:
            raise RuntimeError(f"{self._name} unavailable")
        return CompletionResponse(
            content=self._response,
            model="test-model",
            provider=self._name,
        )


@pytest.mark.asyncio
async def test_router_uses_first_enabled_provider():
    primary = _FakeProvider("primary", enabled=True, response="result from primary")
    secondary = _FakeProvider(
        "secondary", enabled=True, response="result from secondary"
    )
    router = InferenceRouter([primary, secondary])
    result = await router.complete("test prompt")
    assert result == "result from primary"
    assert primary.calls == 1
    assert secondary.calls == 0


@pytest.mark.asyncio
async def test_router_falls_back_on_failure():
    failing = _FakeProvider("failing", enabled=True, response=None)
    fallback = _FakeProvider("fallback", enabled=True, response="fallback result")
    router = InferenceRouter([failing, fallback])
    result = await router.complete("test prompt")
    assert result == "fallback result"
    assert failing.calls == 1
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_router_returns_none_when_all_fail():
    p1 = _FakeProvider("p1", enabled=True, response=None)
    p2 = _FakeProvider("p2", enabled=True, response=None)
    router = InferenceRouter([p1, p2])
    result = await router.complete("test prompt")
    assert result is None


def test_router_disabled_when_no_providers_enabled():
    p = _FakeProvider("disabled", enabled=False)
    router = InferenceRouter([p])
    assert not router.enabled


def test_router_enabled_when_at_least_one_provider_enabled():
    enabled = _FakeProvider("openai", enabled=True, response="ok")
    disabled = _FakeProvider("ollama", enabled=False)
    router = InferenceRouter([enabled, disabled])
    assert router.enabled
    assert router.active_provider == "openai"


@pytest.mark.asyncio
async def test_router_skips_disabled_providers():
    disabled = _FakeProvider("disabled", enabled=False)
    active = _FakeProvider("active", enabled=True, response="hello")
    router = InferenceRouter([disabled, active])
    result = await router.complete("prompt")
    assert result == "hello"
    assert disabled.calls == 0


@pytest.mark.asyncio
async def test_disabled_embedding_provider_raises():
    provider = DisabledEmbeddingProvider()
    assert not provider.enabled
    with pytest.raises(RuntimeError):
        await provider.embed("test")
