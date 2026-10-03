"""Tests for environment-backed configuration."""

from app.config import Settings
from app.db.config import database_is_configured, get_database_url
from pydantic import SecretStr


def test_settings_accepts_groq_compatible_configuration() -> None:
    settings = Settings(
        llm_provider="groq",
        llm_base_url="https://llm.example.test/v1",
        llm_api_key=SecretStr("test-key"),
        llm_model="test-model",
    )

    assert settings.llm_provider == "groq"
    assert str(settings.llm_base_url) == "https://llm.example.test/v1"
    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "test-key"


def test_database_configuration_is_optional_and_never_required_at_startup() -> None:
    settings = Settings(database_url=None)

    assert get_database_url(settings) is None
    assert database_is_configured(settings) is False


def test_database_configuration_accepts_supabase_postgresql_url() -> None:
    database_url = "postgresql+asyncpg://postgres:password@db.example.test:5432/postgres"
    settings = Settings(database_url=SecretStr(database_url))

    assert get_database_url(settings) == database_url
    assert database_is_configured(settings) is True
