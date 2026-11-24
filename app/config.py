"""Configuration management using Pydantic Settings.

Demonstrates production-grade config: typed settings, env var loading,
and validation at startup instead of scattered os.getenv calls.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FDE Portfolio Service"
    environment: str = Field(default="dev", description="dev | staging | prod")
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8000

    # Placeholder for the LLM endpoint that will be added in week 2.
    llm_api_base: str = ""
    llm_api_key: str = ""

    @property
    def is_prod(self) -> bool:
        return self.environment.lower() == "prod"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (fast, validated once)."""
    return Settings()
