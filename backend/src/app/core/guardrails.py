from collections.abc import Callable

from app.core.pii_guard import redact_pii

BeforeHookResult = tuple[str, list[str]]  # (processed_text, notes)


def before_hook_redact_pii(text: str) -> BeforeHookResult:
    redacted, found = redact_pii(text)
    notes = [f"redacted {label}" for label in found]
    return redacted, notes


BEFORE_HOOKS: list[Callable[[str], BeforeHookResult]] = [
    before_hook_redact_pii,
]


def run_before_hooks(text: str) -> BeforeHookResult:
    """Runs every registered before-hook in sequence over the given text —
    the single entry point every prompt-construction site should call,
    instead of hand-picking which safety checks to remember to apply.
    """
    all_notes: list[str] = []
    processed = text

    for hook in BEFORE_HOOKS:
        processed, notes = hook(processed)
        all_notes.extend(notes)

    return processed, all_notes
