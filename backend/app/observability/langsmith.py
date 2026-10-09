from __future__ import annotations

import os

from app.config import get_settings


def configure_langsmith() -> None:
    """Configure LangSmith tracing from application settings."""

    settings = get_settings()

    if not settings.langsmith_tracing:
        return

    if not settings.langsmith_api_key:
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = (
        settings.langsmith_api_key.get_secret_value()
    )
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint