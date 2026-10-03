"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings

SettingsDependency = Annotated[Settings, Depends(get_settings)]
