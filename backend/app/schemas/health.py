"""Schemas for operational endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Public response contract for the backend health check."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    service: str
    version: str
    environment: str
