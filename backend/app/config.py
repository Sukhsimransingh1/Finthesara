"""Environment-backed application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "agentic-finance-research"
    app_environment: Literal["local", "development", "test", "staging", "production"] = "local"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    database_url: SecretStr | None = None
    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    embedding_dimension: int = Field(default=768, ge=1, le=10000)

    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "agentic-finance-research-local"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    llm_provider: str = "groq"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: SecretStr | None = None
    llm_model: str = "openai/gpt-oss-20b"
    llm_timeout_seconds: int = Field(default=30, ge=1, le=300)
    sec_user_agent: str = ""

@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
