"""Explicit async SQLAlchemy connection construction.

Creating an engine is configuration-only: no network connection is opened until
the returned session is used by an explicitly invoked repository operation.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.db.config import get_database_url


@dataclass(frozen=True)
class Database:
    """Own the explicit async engine and session factory for an application process."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


def create_database(settings: Settings) -> Database | None:
    """Create database access objects only when a PostgreSQL URL is configured."""

    database_url = get_database_url(settings)
    if database_url is None:
        return None

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return Database(engine=engine, session_factory=session_factory)
