"""Database configuration helpers without opening a connection."""

from sqlalchemy.engine import make_url

from app.config import Settings


def get_database_url(settings: Settings) -> str | None:
    """Return the configured async PostgreSQL URL, if supplied."""

    if settings.database_url is None:
        return None
    return settings.database_url.get_secret_value()


def database_is_configured(settings: Settings) -> bool:
    """Report whether a valid PostgreSQL configuration has been supplied."""

    database_url = get_database_url(settings)
    if database_url is None:
        return False
    return make_url(database_url).drivername.startswith("postgresql")
