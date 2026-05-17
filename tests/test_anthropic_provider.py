"""Tests for AnthropicProvider prompt caching and extended thinking."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.inference.anthropic_provider import AnthropicProvider
from src.inference.base_provider import CompletionRequest


def _make_response(
    text: str = "test response",
    cache_read: int = 0,
    cache_write: int = 0,
    input_tokens: int = 100,
    output_tokens: int = 20,
) -> MagicMock:
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        "content": [{"type": "text", "text": text}],
        "model": "claude-haiku-4-5-20251001",
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_write,
        },
    }
    return mock


@pytest.mark.asyncio
async def test_anthropic_provider_disabled_when_no_key():
    provider = AnthropicProvider(api_key="", model="claude-haiku-4-5-20251001")
    assert not provider.enabled


def test_anthropic_provider_properties():
    provider = AnthropicProvider(
        api_key="sk-ant-test",
        model="claude-haiku-4-5-20251001",
        reasoning_tier="fast",
    )
    assert provider.name == "anthropic"
    assert provider.enabled
    assert provider.reasoning_tier == "fast"


@pytest.mark.asyncio
async def test_cache_write_on_first_request():
    provider = AnthropicProvider(api_key="sk-ant-test", model="claude-haiku-4-5-20251001")
    mock_resp = _make_response(cache_write=500, cache_read=0)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        req = CompletionRequest(prompt="test", system="You are a research assistant.")
        result = await provider.complete(req)

    assert result.cache_write_tokens == 500
    assert result.cached_tokens is None  # first request — no hit yet


@pytest.mark.asyncio
async def test_cache_hit_on_subsequent_request():
    provider = AnthropicProvider(api_key="sk-ant-test", model="claude-haiku-4-5-20251001")
    # cache_read=500 simulates a warm cache hit (0.1x price)
    mock_resp = _make_response(cache_read=500, cache_write=0)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        req = CompletionRequest(prompt="test", system="You are a research assistant.")
        result = await provider.complete(req)

    assert result.cached_tokens == 500
    assert result.cache_write_tokens is None


@pytest.mark.asyncio
async def test_cache_control_in_payload():
    """Verify cache_control block is included in the system message."""
    provider = AnthropicProvider(api_key="sk-ant-test", model="claude-haiku-4-5-20251001")
    mock_resp = _make_response()
    captured_payload: dict = {}

    async def capture_post(url: str, headers: dict, json: dict):
        captured_payload.update(json)
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=capture_post)
        mock_client_cls.return_value = mock_client

        req = CompletionRequest(prompt="hello", system="System context")
        await provider.complete(req)

    system_blocks = captured_payload.get("system", [])
    assert len(system_blocks) == 1
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert system_blocks[0]["text"] == "System context"


@pytest.mark.asyncio
async def test_extended_thinking_sets_temperature_1():
    """thinking_budget > 0 must set temperature=1 (API requirement)."""
    provider = AnthropicProvider(api_key="sk-ant-test", model="claude-sonnet-4-6")
    mock_resp = _make_response()
    captured_payload: dict = {}

    async def capture_post(url: str, headers: dict, json: dict):
        captured_payload.update(json)
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=capture_post)
        mock_client_cls.return_value = mock_client

        req = CompletionRequest(prompt="complex proof", system="Reason carefully", thinking_budget=2048)
        await provider.complete(req)

    assert captured_payload.get("temperature") == 1
    assert captured_payload.get("thinking") == {"type": "enabled", "budget_tokens": 2048}


@pytest.mark.asyncio
async def test_no_thinking_when_budget_zero():
    provider = AnthropicProvider(api_key="sk-ant-test", model="claude-haiku-4-5-20251001")
    mock_resp = _make_response()
    captured_payload: dict = {}

    async def capture_post(url: str, headers: dict, json: dict):
        captured_payload.update(json)
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=capture_post)
        mock_client_cls.return_value = mock_client

        req = CompletionRequest(prompt="simple question", system="Be concise")
        await provider.complete(req)

    assert "thinking" not in captured_payload
    assert captured_payload.get("temperature") == pytest.approx(0.7)
