import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.inference.base_provider import CompletionRequest, ThinkingConfig
from src.inference.anthropic_provider import AnthropicProvider


@pytest.mark.asyncio
async def test_anthropic_provider_complete_sends_correct_payload():
    provider = AnthropicProvider(api_key="mock-key", model="claude-3-7-sonnet-20250219")
    req = CompletionRequest(
        prompt="Describe the universe",
        system="Be scientific.",
        thinking=ThinkingConfig(enabled=True, budget_tokens=1024),
        enable_caching=True
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [
            {"type": "text", "text": "The universe is big."}
        ],
        "model": "claude-3-7-sonnet-20250219",
        "usage": {
            "output_tokens": 10,
            "input_tokens": 100,
            "cache_read_input_tokens": 80,
            "cache_creation_input_tokens": 20
        }
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        resp = await provider.complete(req)
        assert resp.content == "The universe is big."
        assert resp.cache_read_tokens == 80
        assert resp.cache_creation_tokens == 20
        
        # Verify prompt cache header and ephemeral controls
        args, kwargs = mock_post.call_args
        headers = kwargs["headers"]
        assert headers["x-api-key"] == "mock-key"
        assert "prompt-caching-2024-07-31" in headers["anthropic-beta"]
        
        json_payload = kwargs["json"]
        assert json_payload["system"][0]["cache_control"] == {"type": "ephemeral"}
        assert json_payload["thinking"] == {"type": "enabled", "budget_tokens": 1024}
