from app.core.settings_tuning import DEFAULT_MAX_RUN_COST_USD


class RunCostExceededError(Exception):
    """Raised when a run's accumulated (or projected) LLM spend crosses
    its configured ceiling. Callers should treat this as a hard stop,
    not something to retry past.
    """


class RunCostTracker:
    """Accumulates estimated USD cost across every LLM call in a single
    investigation+implementation run, and refuses to let the run spend
    past a hard ceiling. This is a governance accumulator, not a billing
    system — pricing constants below are rough blended estimates, not
    live provider rates.
    """

    # USD per 1K tokens, rough OpenRouter CAPABLE-tier estimate. Update
    # against real provider pricing before relying on this for anything
    # beyond a coarse safety net.
    COST_PER_1K_INPUT_TOKENS = 0.0015
    COST_PER_1K_OUTPUT_TOKENS = 0.006

    def __init__(self, max_estimated_cost_usd: float = DEFAULT_MAX_RUN_COST_USD):
        self.max_estimated_cost_usd = max_estimated_cost_usd
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens / 1000 * self.COST_PER_1K_INPUT_TOKENS
            + output_tokens / 1000 * self.COST_PER_1K_OUTPUT_TOKENS
        )

    def check_before_call(self, estimated_input_tokens: int, estimated_output_tokens: int) -> None:
        """Checked BEFORE a call is made, not just after — a worst-case
        estimate of the upcoming call's cost is projected against the
        running total so we never fire off a call already known to blow
        the budget.
        """
        projected = self.total_cost_usd + self._estimate_cost(
            estimated_input_tokens, estimated_output_tokens
        )
        if projected > self.max_estimated_cost_usd:
            raise RunCostExceededError(
                f"Projected run cost ${projected:.4f} would exceed ceiling "
                f"${self.max_estimated_cost_usd:.4f} — refusing to make the call"
            )

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Called AFTER a call completes, with its actual token usage."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += self._estimate_cost(input_tokens, output_tokens)
        self.raise_if_exceeded()

    def raise_if_exceeded(self) -> None:
        if self.total_cost_usd > self.max_estimated_cost_usd:
            raise RunCostExceededError(
                f"Run cost ${self.total_cost_usd:.4f} exceeded ceiling "
                f"${self.max_estimated_cost_usd:.4f}"
            )
