from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(settings: Annotated[Settings, Depends(get_settings)],) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }