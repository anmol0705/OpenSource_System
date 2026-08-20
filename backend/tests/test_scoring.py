from app.core.issue_scoring import score_issue
from app.core.scoring import score_repository


def test_score_repository_rewards_recent_activity() -> None:
    active_repo = {
        "stargazers_count": 5000,
        "open_issues_count": 20,
        "pushed_at": "2026-08-19T00:00:00Z",  # pushed yesterday relative to "today" in these tests
    }
    stale_repo = {
        "stargazers_count": 5000,
        "open_issues_count": 20,
        "pushed_at": "2025-01-01T00:00:00Z",  # long stale
    }

    active_score, _ = score_repository(active_repo)
    stale_score, _ = score_repository(stale_repo)

    assert active_score > stale_score


def test_score_repository_with_zero_open_issues_has_no_accessibility() -> None:
    repo = {"stargazers_count": 1000, "open_issues_count": 0, "pushed_at": "2026-08-19T00:00:00Z"}
    _, breakdown = score_repository(repo)
    assert breakdown["contribution_accessibility"] == 0.0


def test_score_issue_rewards_skill_match() -> None:
    profile_skills = {"languages": {"python": "advanced"}, "domains": ["backend"]}

    matching_issue = {
        "title": "Fix backend bug in python parser",
        "body": "x" * 500,
        "updated_at": "2026-08-19T00:00:00Z",
        "assignee": None,
    }
    non_matching_issue = {
        "title": "Update documentation formatting",
        "body": "x" * 500,
        "updated_at": "2026-08-19T00:00:00Z",
        "assignee": None,
    }

    match_score, _ = score_issue(matching_issue, profile_skills)
    no_match_score, _ = score_issue(non_matching_issue, profile_skills)

    assert match_score > no_match_score


def test_score_issue_penalizes_already_claimed() -> None:
    profile_skills = {"languages": {}, "domains": []}
    base_issue = {
        "title": "Some issue",
        "body": "x" * 500,
        "updated_at": "2026-08-19T00:00:00Z",
    }

    unclaimed_score, _ = score_issue({**base_issue, "assignee": None}, profile_skills)
    claimed_score, _ = score_issue({**base_issue, "assignee": {"login": "someone"}}, profile_skills)

    assert unclaimed_score > claimed_score
