import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Issue


async def upsert_issue(
    db: AsyncSession,
    repository_id: uuid.UUID,
    issue_data: dict[str, Any],
    score: float,
    breakdown: dict[str, Any],
) -> Issue:
    number = issue_data["number"]

    result = await db.execute(
        select(Issue).where(
            Issue.repository_id == repository_id, Issue.github_issue_number == number
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.title = issue_data["title"]
        existing.body = issue_data.get("body")
        existing.labels = [label["name"] for label in issue_data.get("labels", [])]
        existing.score = score
        existing.score_breakdown = breakdown
        issue_row = existing
    else:
        issue_row = Issue(
            repository_id=repository_id,
            github_issue_number=number,
            title=issue_data["title"],
            body=issue_data.get("body"),
            labels=[label["name"] for label in issue_data.get("labels", [])],
            score=score,
            score_breakdown=breakdown,
        )
        db.add(issue_row)

    await db.commit()
    await db.refresh(issue_row)
    return issue_row
