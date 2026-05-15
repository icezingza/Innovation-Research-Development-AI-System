from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    postgres_url: str = (
        "postgresql+asyncpg://cognitive:cognitive@localhost/cognition"
    )
    redis_url: str = "redis://localhost:6379"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # OpenAI-compatible inference — leave blank to run without LLM
    inference_base_url: str = "https://api.openai.com/v1"
    inference_api_key: str = ""
    inference_model: str = "gpt-4o-mini"

    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
