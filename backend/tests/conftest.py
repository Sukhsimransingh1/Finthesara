"""Shared test configuration."""

from collections.abc import Generator

import pytest
from app.config import get_settings
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    """Keep environment-backed settings isolated between tests."""

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the ASGI application."""

    return TestClient(app)
