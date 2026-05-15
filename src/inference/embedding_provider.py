import asyncio
import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)

_KNOWN_DIMS: dict[str, int] = {
    "all-MiniLM-L6-v2": 384,
    "all-MiniLM-L12-v2": 384,
    "all-mpnet-base-v2": 768,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class BaseEmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @property
    @abstractmethod
    def enabled(self) -> bool: ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI-compatible embedding provider."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._enabled = bool(api_key)

    @property
    def dimensions(self) -> int:
        return _KNOWN_DIMS.get(self._model, 1536)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "input": text},
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Sentence-transformers local embedding — no API key required.

    Model is lazy-loaded on first embed() call to avoid blocking startup.
    Falls back to disabled state if sentence-transformers is not installed.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None
        self._dims = _KNOWN_DIMS.get(model_name, 384)
        self._load_failed = False

    @property
    def dimensions(self) -> int:
        return self._dims

    @property
    def enabled(self) -> bool:
        return not self._load_failed

    def _load(self) -> None:
        if self._model is not None or self._load_failed:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            self._dims = self._model.get_sentence_embedding_dimension()
            logger.info(
                "local_embedding_model_loaded", extra={"model": self._model_name}
            )
        except Exception as exc:
            self._load_failed = True
            logger.error(
                "local_embedding_model_failed",
                extra={"model": self._model_name, "error": str(exc)},
            )
            raise

    async def embed(self, text: str) -> list[float]:
        self._load()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._model.encode(text, convert_to_numpy=True).tolist(),
        )


class DisabledEmbeddingProvider(BaseEmbeddingProvider):
    """Fallback when no embedding provider is configured."""

    @property
    def dimensions(self) -> int:
        return 384

    @property
    def enabled(self) -> bool:
        return False

    async def embed(self, text: str) -> list[float]:
        raise RuntimeError("No embedding provider configured")
