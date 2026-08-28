import re

# Patterns are intentionally conservative (favor false positives over
# false negatives) — better to over-redact a false match than leak a
# real credential. Each pattern is named so redacted output shows WHAT
# kind of thing was caught, useful for debugging false positives later.
PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "GITHUB_TOKEN": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "GENERIC_API_KEY": re.compile(r"\b(?:sk|pk|api|key)[-_][A-Za-z0-9]{20,}\b", re.IGNORECASE),
    "AWS_ACCESS_KEY": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Scans text for PII-shaped patterns and replaces each match with a
    labeled placeholder. Returns (redacted_text, list_of_types_found) —
    the list lets callers log/alert on what was caught without needing
    to re-scan, and without logging the actual sensitive value itself.
    """
    found: list[str] = []
    redacted = text

    for label, pattern in PII_PATTERNS.items():
        matches = pattern.findall(redacted)
        if matches:
            found.append(label)
            redacted = pattern.sub(f"[REDACTED_{label}]", redacted)

    return redacted, found
