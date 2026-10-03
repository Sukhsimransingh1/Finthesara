"""Health endpoint for service and container checks."""

from fastapi import APIRouter

from app.api.deps import SettingsDependency
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Check backend health")
async def health_check(settings: SettingsDependency) -> HealthResponse:
    """Return local process health without probing future dependencies."""

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_environment,
    )
