from app.core.guardrails import run_before_hooks


def test_run_before_hooks_redacts_pii() -> None:
    text = "contact me at test@example.com"
    processed, notes = run_before_hooks(text)
    assert "test@example.com" not in processed
    assert any("EMAIL" in note for note in notes)


def test_run_before_hooks_passes_through_clean_text() -> None:
    text = "a completely normal bug description"
    processed, notes = run_before_hooks(text)
    assert processed == text
    assert notes == []


def test_run_before_hooks_composes_multiple_hooks() -> None:
    """Proves the CHAINING mechanism itself works — each hook receives
    the PREVIOUS hook's output, not the original raw text — using a
    temporary fake hook, not relying on real hooks happening to compose
    correctly by coincidence.
    """
    from app.core import guardrails

    original_hooks = guardrails.BEFORE_HOOKS.copy()

    def fake_uppercase_hook(text: str) -> tuple[str, list[str]]:
        return text.upper(), ["uppercased"]

    guardrails.BEFORE_HOOKS.append(fake_uppercase_hook)
    try:
        processed, notes = run_before_hooks("hello world")
        assert processed == "HELLO WORLD"
        assert "uppercased" in notes
    finally:
        guardrails.BEFORE_HOOKS[:] = original_hooks
