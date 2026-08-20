import math
from datetime import UTC, datetime
from typing import Any


def score_repository(repo: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """Deterministic repository score. Returns (final_score, breakdown) —
    we always keep the breakdown so a low/high score is explainable,
    not a black box.
    """
    stars = repo.get("stargazers_count", 0)
    open_issues = repo.get("open_issues_count", 0)
    pushed_at = repo.get("pushed_at")

    project_quality = min(math.log10(stars + 1) / 5, 1.0)

    maintainer_activity = 0.0
    if pushed_at:
        last_push = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        days_since_push = (datetime.now(UTC) - last_push).days
        maintainer_activity = max(0.0, 1.0 - (days_since_push / 180))

    contribution_accessibility = 0.0 if open_issues == 0 else min(open_issues / 50, 1.0)

    abandonment_risk = 1.0 - maintainer_activity

    breakdown = {
        "project_quality": round(project_quality, 3),
        "maintainer_activity": round(maintainer_activity, 3),
        "contribution_accessibility": round(contribution_accessibility, 3),
        "abandonment_risk_penalty": round(abandonment_risk, 3),
    }

    final_score = (
        0.35 * project_quality
        + 0.30 * maintainer_activity
        + 0.25 * contribution_accessibility
        - 0.20 * abandonment_risk
    )
    final_score = max(0.0, round(final_score, 3))

    return final_score, breakdown
