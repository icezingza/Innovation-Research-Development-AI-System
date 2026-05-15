from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Infrastructure ---
    postgres_url: str = (
        "postgresql+asyncpg://cognitive:cognitive@localhost/cognition"
    )
    redis_url: str = "redis://localhost:6379"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # --- OpenAI-compatible inference ---
    # Works with OpenAI, OpenRouter, vLLM, LM Studio — leave blank for heuristic mode
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4.1-mini"

    # --- Ollama (local inference) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- Embeddings ---
    # OpenAI: text-embedding-3-small | Local: all-MiniLM-L6-v2
    embedding_model: str = "text-embedding-3-small"
    embedding_model_local: str = "all-MiniLM-L6-v2"

    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
