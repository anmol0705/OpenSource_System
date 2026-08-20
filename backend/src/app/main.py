from fastapi import FastAPI  # type: ignore

from app.core.config import get_settings
from app.routers import health

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(health.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Autonomous Open-Source Apprenticeship System — backend is alive"}
