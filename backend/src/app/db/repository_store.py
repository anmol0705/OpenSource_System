from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Repository


async def upsert_repository(
    db: AsyncSession, repo_data: dict[str, Any], score: float, breakdown: dict[str, Any]
) -> Repository:
    """Insert a new repository row, or update it if we've already seen
    this repo before (matched by GitHub's full_name).
    """
    full_name = repo_data["full_name"]

    result = await db.execute(select(Repository).where(Repository.github_full_name == full_name))
    existing = result.scalar_one_or_none()

    if existing:
        existing.description = repo_data.get("description")
        existing.stars = repo_data.get("stargazers_count", 0)
        existing.primary_language = repo_data.get("language")
        existing.score = score
        existing.score_breakdown = breakdown
        repo_row = existing
    else:
        repo_row = Repository(
            github_full_name=full_name,
            description=repo_data.get("description"),
            stars=repo_data.get("stargazers_count", 0),
            primary_language=repo_data.get("language"),
            score=score,
            score_breakdown=breakdown,
        )
        db.add(repo_row)

    await db.commit()
    await db.refresh(repo_row)
    return repo_row
