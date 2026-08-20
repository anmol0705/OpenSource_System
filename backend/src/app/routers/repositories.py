import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.github_client import GitHubClient, get_github_client
from app.core.issue_scoring import score_issue
from app.core.scoring import score_repository
from app.db.issue_store import upsert_issue
from app.db.models import DeveloperProfile, Repository
from app.db.repository_store import upsert_repository
from app.db.session import get_db

router = APIRouter(prefix="/repos", tags=["repositories"])


@router.post("/discover")
async def discover_repositories(
    query: str,
    limit: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    github: Annotated[GitHubClient, Depends(get_github_client)],
) -> list[dict[str, Any]]:
    """Search GitHub, score every result deterministically, persist
    all of it, and return the ranked list — highest score first.
    """
    raw_repos = await github.search_repositories(query, limit=limit)

    results: list[dict[str, Any]] = []
    for repo_data in raw_repos:
        score, breakdown = score_repository(repo_data)
        saved = await upsert_repository(db, repo_data, score, breakdown)
        results.append(
            {
                "full_name": saved.github_full_name,
                "score": saved.score,
                "breakdown": saved.score_breakdown,
                "stars": saved.stars,
            }
        )

    await github.close()
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


@router.post("/{full_name:path}/issues/discover")
async def discover_issues(
    full_name: str,
    profile_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    github: Annotated[GitHubClient, Depends(get_github_client)],
) -> list[dict[str, Any]]:
    """Fetch open issues for a repository we've already discovered, score
    each one against the given developer profile, persist, and return
    the ranked list — highest score first.
    """
    repo_result = await db.execute(
        select(Repository).where(Repository.github_full_name == full_name)
    )
    repository = repo_result.scalar_one_or_none()
    if repository is None:
        return []

    profile_result = await db.execute(
        select(DeveloperProfile).where(DeveloperProfile.id == profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        return []

    raw_issues = await github.list_open_issues(full_name)

    results: list[dict[str, Any]] = []
    for issue_data in raw_issues:
        score, breakdown = score_issue(issue_data, profile.skills)
        saved = await upsert_issue(db, repository.id, issue_data, score, breakdown)
        results.append(
            {
                "number": saved.github_issue_number,
                "title": saved.title,
                "score": saved.score,
                "breakdown": saved.score_breakdown,
            }
        )

    await github.close()
    results.sort(key=lambda r: r["score"], reverse=True)
    return results
