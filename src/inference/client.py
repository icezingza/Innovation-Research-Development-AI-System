"""Factory module — creates an InferenceRouter wired from Settings."""
from src.config import Settings
from src.inference.embedding_provider import (
    BaseEmbeddingProvider,
    DisabledEmbeddingProvider,
    LocalEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from src.inference.gemini_provider import GeminiProvider
from src.inference.ollama_provider import OllamaProvider
from src.inference.openai_provider import OpenAIProvider
from src.inference.router import InferenceRouter


def create_inference_router(settings: Settings) -> InferenceRouter:
    """Build a provider list from settings and return a configured router.

    Provider priority:
      1. OpenAI-compatible (if OPENAI_API_KEY is set)
      2. Gemini (if GEMINI_API_KEY is set)
      3. Ollama (always included; probe() checks reachability at startup)
    """
    providers = []

    if settings.openai_api_key:
        providers.append(
            OpenAIProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.default_model,
            )
        )

    if settings.gemini_api_key:
        # Fast tier (Flash)
        providers.append(
            GeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model_fast,
                reasoning_tier="fast",
            )
        )
        # Deep tier (Pro)
        providers.append(
            GeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model_deep,
                reasoning_tier="deep",
            )
        )

    providers.append(
        OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)
    )

    return InferenceRouter(providers)


def create_embedding_provider(settings: Settings) -> BaseEmbeddingProvider:
    """Select embedding provider based on settings.

    Priority:
      1. OpenAI embeddings (if OPENAI_API_KEY is set)
      2. Local sentence-transformers
      3. Disabled (graceful degradation)
    """
    if settings.openai_api_key:
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.embedding_model,
        )
    try:
        return LocalEmbeddingProvider(model_name=settings.embedding_model_local)
    except Exception:
        return DisabledEmbeddingProvider()
