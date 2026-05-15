import logging

import httpx

from src.config import Settings

logger = logging.getLogger(__name__)


class InferenceClient:
    """Async OpenAI-compatible inference client.

    When inference_api_key is empty the client operates in disabled mode —
    complete() returns None and callers fall back to heuristic reasoning.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.inference_base_url.rstrip("/")
        self._api_key = settings.inference_api_key
        self._model = settings.inference_model
        self._enabled = bool(self._api_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def complete(
        self,
        prompt: str,
        system: str = "You are a scientific reasoning assistant.",
        temperature: float = 0.7,
    ) -> str | None:
        if not self._enabled:
            return None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperature,
                    },
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception:
            logger.exception("inference_request_failed")
            return None
