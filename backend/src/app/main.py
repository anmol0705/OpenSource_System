from fastapi import FastAPI

from app.core.config import get_settings
from app.routers import health, profiles, repositories, sandboxes

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(health.router)
app.include_router(repositories.router)
app.include_router(profiles.router)
app.include_router(sandboxes.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Autonomous Open-Source Apprenticeship System — backend is alive"}
