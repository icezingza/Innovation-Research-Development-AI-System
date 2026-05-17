import pytest
from unittest.mock import AsyncMock, patch
from src.inference.gemini_provider import GeminiProvider
from src.inference.base_provider import CompletionRequest


@pytest.mark.anyio
async def test_gemini_provider_complete_success():
    # Mock response data
    mock_response_data = {
        "candidates": [
            {
                "content": {"parts": [{"text": "Hello from Gemini!"}], "role": "model"},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"totalTokenCount": 15},
    }

    # Mock httpx response
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    # Initialize provider
    provider = GeminiProvider(api_key="test-key", model="gemini-1.5-flash")

    # Patch httpx.AsyncClient.post
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        request = CompletionRequest(
            prompt="Hello", system="You are a helpful assistant"
        )
        response = await provider.complete(request)

        # Assertions
        assert response.content == "Hello from Gemini!"
        assert response.model == "gemini-1.5-flash"
        assert response.provider == "gemini-provider"
        assert response.tokens_used == 15

        # Check if post was called with correct payload
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        assert payload["contents"][0]["parts"][0]["text"] == "Hello"
        assert (
            payload["system_instruction"]["parts"][0]["text"]
            == "You are a helpful assistant"
        )
        assert kwargs["headers"]["x-goog-api-key"] == "test-key"


@pytest.mark.anyio
async def test_gemini_provider_error_handling():
    # Mock httpx response with error
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Invalid API Key"
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")

    provider = GeminiProvider(api_key="invalid-key", model="gemini-1.5-flash")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        request = CompletionRequest(prompt="Hello")
        with pytest.raises(Exception):
            await provider.complete(request)


@pytest.mark.anyio
async def test_gemini_provider_caching_and_thinking_payload():
    from src.inference.base_provider import CompletionRequest, ThinkingConfig
    from src.inference.gemini_provider import GeminiProvider
    from unittest.mock import MagicMock

    provider = GeminiProvider(api_key="mock-gemini-key", model="gemini-2.0-flash")
    req = CompletionRequest(
        prompt="Research details",
        system="Deep scientific research rules.",
        thinking=ThinkingConfig(enabled=True, budget_tokens=2048),
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Synthesis done."}]}}],
        "usageMetadata": {"totalTokenCount": 150, "cachedContentTokenCount": 80},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        resp = await provider.complete(req)
        assert resp.content == "Synthesis done."
        assert resp.cached_tokens == 80

        args, kwargs = mock_post.call_args
        json_payload = kwargs["json"]
        assert "system_instruction" in json_payload
        assert (
            json_payload["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 2048
        )
