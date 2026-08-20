from datetime import UTC, datetime
from typing import Any


def score_issue(
    issue: dict[str, Any], profile_skills: dict[str, Any]
) -> tuple[float, dict[str, float]]:
    """Deterministic issue score against a developer profile.

    Several terms from the original IssueScore design (CareerRelevance,
    EstimatedImpact, MergeProbability, NovelSkillValue) genuinely need
    LLM judgment or historical outcome data we don't have yet — those
    are stubbed at a neutral 0.5 for now, clearly labeled, rather than
    faked with a fancier-looking formula we can't actually justify.
    """
    title = issue.get("title", "") or ""
    body = issue.get("body", "") or ""
    text = f"{title} {body}".lower()

    languages = [lang.lower() for lang in profile_skills.get("languages", {})]
    domains = [d.lower().replace("_", " ") for d in profile_skills.get("domains", [])]

    # --- SkillFit: crude keyword overlap for now (Phase 3 upgrades this to embeddings) ---
    lang_hits = sum(1 for lang in languages if lang in text)
    domain_hits = sum(1 for domain in domains if domain in text)
    total_terms = max(len(languages) + len(domains), 1)
    skill_fit = min((lang_hits + domain_hits) / total_terms, 1.0)

    # --- IssueClarity: is there enough written context to actually act on? ---
    issue_clarity = min(len(body) / 500, 1.0) if body else 0.0

    # --- StalenessPenalty: issue open a long time with no recent update ---
    updated_at = issue.get("updated_at")
    staleness_penalty = 0.0
    if updated_at:
        last_update = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        days_stale = (datetime.now(UTC) - last_update).days
        staleness_penalty = min(days_stale / 365, 1.0)

    # --- AlreadyClaimedPenalty: someone's already assigned ---
    already_claimed_penalty = 1.0 if issue.get("assignee") else 0.0

    # --- Stubbed terms — neutral placeholder until Phase 4+ gives us real signal ---
    learning_value = 0.5  # needs LLM judgment on what concepts the issue teaches
    merge_probability = 0.5  # needs historical outcome data (Phase 8's contribution ledger)
    career_relevance = 0.5  # needs LLM judgment against profile goals
    novel_skill_value = 0.5  # needs a comparison against skills you already have
    estimated_impact = 0.5  # needs LLM judgment on issue significance

    breakdown = {
        "skill_fit": round(skill_fit, 3),
        "issue_clarity": round(issue_clarity, 3),
        "learning_value_stub": learning_value,
        "merge_probability_stub": merge_probability,
        "career_relevance_stub": career_relevance,
        "novel_skill_value_stub": novel_skill_value,
        "estimated_impact_stub": estimated_impact,
        "staleness_penalty": round(staleness_penalty, 3),
        "already_claimed_penalty": already_claimed_penalty,
    }

    final_score = (
        0.22 * skill_fit
        + 0.20 * learning_value
        + 0.15 * merge_probability
        + 0.12 * issue_clarity
        + 0.08 * career_relevance
        + 0.07 * novel_skill_value
        + 0.06 * estimated_impact
        - 0.15 * staleness_penalty
        - 0.20 * already_claimed_penalty
    )
    final_score = max(0.0, round(final_score, 3))

    return final_score, breakdown
