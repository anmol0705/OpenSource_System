from app.core.pii_guard import redact_pii


def test_redacts_email() -> None:
    text = "Contact me at john.doe@example.com for details"
    redacted, found = redact_pii(text)
    assert "john.doe@example.com" not in redacted
    assert "EMAIL" in found
    assert "[REDACTED_EMAIL]" in redacted


def test_redacts_github_token() -> None:
    text = "my token is ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    redacted, found = redact_pii(text)
    assert "ghp_abcdefghijklmnopqrstuvwxyz1234567890" not in redacted
    assert "GITHUB_TOKEN" in found


def test_leaves_clean_text_unchanged() -> None:
    text = "This is a normal bug report about a null pointer exception."
    redacted, found = redact_pii(text)
    assert redacted == text
    assert found == []


def test_redacts_multiple_pii_types_in_one_text() -> None:
    text = "Email me at test@test.com, my key is sk-abc123def456ghi789jkl"
    redacted, found = redact_pii(text)
    assert "test@test.com" not in redacted
    assert "sk-abc123def456ghi789jkl" not in redacted
    assert set(found) == {"EMAIL", "GENERIC_API_KEY"}
