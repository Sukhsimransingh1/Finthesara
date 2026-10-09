"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.research import router as research_router
from app.api.v1.router import router as api_v1_router
from app.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Create the API application without performing external connections."""

    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend foundation for agentic-finance-research.",
    )
    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(research_router)
    return app


app = create_app()
