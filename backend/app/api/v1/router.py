
"""Version 1 API router composition."""

from fastapi import APIRouter

from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.human_reviews import router as human_reviews_router
from app.api.v1.research_runs import router as research_runs_router

router = APIRouter()

router.include_router(health_router)
router.include_router(documents_router)
router.include_router(research_runs_router)
router.include_router(human_reviews_router)