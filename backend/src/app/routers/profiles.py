from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DeveloperProfile
from app.db.session import get_db

router = APIRouter(prefix="/profiles", tags=["profiles"])


class CreateProfileRequest(BaseModel):
    name: str
    languages: dict[str, str]
    domains: list[str]


@router.post("")
async def create_profile(
    payload: CreateProfileRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    profile = DeveloperProfile(
        name=payload.name,
        skills={"languages": payload.languages, "domains": payload.domains},
        preferences={},
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return {"id": str(profile.id), "name": profile.name, "skills": profile.skills}
