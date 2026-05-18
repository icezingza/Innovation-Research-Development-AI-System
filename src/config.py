from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Infrastructure ---
    postgres_url: str = "postgresql+asyncpg://app_user:app_secret@localhost/cognition"
    redis_url: str = "redis://localhost:6379"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # --- Anthropic (native API — enables prompt caching + extended thinking) ---
    # Cache hit = 0.1x input cost. Stack with batch API = 0.05x total.
    # Fast: claude-haiku-4-5-20251001  Deep: claude-sonnet-4-6
    anthropic_api_key: str = ""
    anthropic_model_fast: str = "claude-haiku-4-5-20251001"
    anthropic_model_deep: str = "claude-sonnet-4-6"

    # --- OpenAI-compatible inference ---
    # Works with OpenAI, OpenRouter, vLLM, LM Studio — leave blank for heuristic mode
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4.1-mini"

    # --- Gemini inference ---
    gemini_api_key: str = ""
    gemini_model_fast: str = "gemini-1.5-flash"
    gemini_model_deep: str = "gemini-1.5-pro"

    # --- Anthropic inference ---
    anthropic_api_key: str = ""

    # --- DeepSeek Inference ---
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # --- OpenRouter Inference ---
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-r1"

    # --- Ollama (local inference) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- Embeddings ---
    # OpenAI: text-embedding-3-small | Local: all-MiniLM-L6-v2
    embedding_model: str = "text-embedding-3-small"
    embedding_model_local: str = "all-MiniLM-L6-v2"

    # --- Security ---
    # Comma-separated API keys. Empty = auth disabled (dev/local mode).
    api_keys: str = ""
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 60

    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
