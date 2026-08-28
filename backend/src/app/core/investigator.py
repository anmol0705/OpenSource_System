from typing import Any, TypedDict, cast

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.guardrails import run_before_hooks
from app.core.llm_router import ModelTier, get_llm
from app.core.sandbox import Sandbox
from app.core.settings_tuning import (
    INVESTIGATION_CONFIDENCE_THRESHOLD,
    MAX_INVESTIGATION_ITERATIONS,
)


class Hypothesis(BaseModel):
    reasoning: str = Field(description="Brief explanation of your current thinking")
    target_file: str = Field(description="The single file path most likely to contain the bug")
    confidence: float = Field(
        description="0.0 to 1.0 — how confident you are this is correct. MUST be a decimal "
        "fraction, e.g. 0.75, never a percentage like 75 or 75.0."
    )
    check_history: bool = Field(
        default=False,
        description="Set true if seeing this file's commit history would help you form a "
        "better hypothesis — e.g. if the current code looks intentional/unusual and you "
        "want to know WHY it's written this way, or whether this bug was fixed before.",
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        if v > 1.0:
            # Model likely returned a percentage (e.g. 30.0 meaning 30%)
            # instead of a 0-1 fraction — normalize rather than silently
            # accept an out-of-range value that would corrupt threshold
            # comparisons downstream. Confirmed real: GLM-5.2 did exactly
            # this during Phase 10 verification testing.
            return v / 100.0
        return max(0.0, min(1.0, v))


class InvestigationState(TypedDict):
    issue_title: str
    issue_body: str
    repo_map_summary: str
    inspected_files: dict[str, str]
    file_histories: dict[str, str]
    hypothesis: str
    target_file: str
    confidence: float
    check_history: bool
    iteration: int
    history: list[str]


def make_form_hypothesis_node() -> Any:
    llm = get_llm(ModelTier.CAPABLE, max_tokens=4096)
    structured_llm = llm.with_structured_output(Hypothesis)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def invoke_with_retry(prompt: str) -> Hypothesis:
        return cast(Hypothesis, structured_llm.invoke(prompt))

    def form_hypothesis(state: InvestigationState) -> dict[str, Any]:
        safe_issue_body, hook_notes = run_before_hooks(state["issue_body"])
        if hook_notes:
            print(f"[guardrails] {hook_notes}")

        inspected_summary = "\n\n".join(
            f"--- {path} ---\n{content[:3000]}"
            for path, content in state["inspected_files"].items()
        )
        history_summary = "\n\n".join(
            f"--- git history for {path} ---\n{log}"
            for path, log in state["file_histories"].items()
        )

        prompt = f"""You are investigating a bug report to find where it likely originates.

ISSUE: {state["issue_title"]}
{safe_issue_body}

REPOSITORY MAP:
{state["repo_map_summary"]}

FILES ALREADY INSPECTED:
{inspected_summary if inspected_summary else "(none yet)"}

GIT HISTORY CHECKED:
{history_summary if history_summary else "(none yet)"}

Based on everything above, form your best hypothesis: which file is most likely
to contain the bug, and how confident are you? If you've already inspected the
right file and are confident, say so. If not, name a NEW file to inspect next.

If you'd benefit from seeing a file's recent commit history (e.g. to check if
this was fixed before, or to understand why the code looks the way it does),
set check_history to true.

IMPORTANT: your confidence should reflect what you've actually verified by
reading real file content above, not just plausible-sounding reasoning from
the repository structure alone. If you have not yet inspected any file,
your confidence should be LOW regardless of how clear the bug seems from
the issue description — inspect the most likely file first."""

        result = invoke_with_retry(prompt)
        next_iteration = state["iteration"] + 1

        return {
            "hypothesis": result.reasoning,
            "target_file": result.target_file,
            "confidence": result.confidence,
            "check_history": result.check_history,
            "iteration": next_iteration,
            "history": state["history"] + [f"iteration {next_iteration}: {result.reasoning}"],
        }

    return form_hypothesis


def make_inspect_file_node(sandbox: Sandbox) -> Any:
    def inspect_file(state: InvestigationState) -> dict[str, Any]:
        path = state["target_file"]
        content = sandbox.read_file(f"/workspace/repo/{path}")

        new_inspected = dict(state["inspected_files"])
        new_inspected[path] = content if content is not None else "(file not found)"

        return {"inspected_files": new_inspected}

    return inspect_file


def make_check_history_node(sandbox: Sandbox) -> Any:
    def check_history(state: InvestigationState) -> dict[str, Any]:
        path = state["target_file"]
        log = sandbox.git_log_for_file(path, limit=5)

        new_histories = dict(state["file_histories"])
        new_histories[path] = log if log else "(no history found)"

        return {"file_histories": new_histories}

    return check_history


def should_continue(state: InvestigationState) -> str:
    # Never allow ending on iteration 1 — force at least one real file
    # inspection before we trust any confidence score. A confidence
    # number the model asserts without having looked at actual code
    # is not evidence, it's just more unverified text.
    if state["iteration"] < 1 or not state["inspected_files"]:
        return "inspect_file"
    if state["check_history"] and state["target_file"] not in state["file_histories"]:
        return "check_history"
    if state["confidence"] >= INVESTIGATION_CONFIDENCE_THRESHOLD:
        return "end"
    if state["iteration"] >= MAX_INVESTIGATION_ITERATIONS:
        return "end"
    return "inspect_file"


def build_investigator_graph(sandbox: Sandbox) -> Any:
    graph = StateGraph(InvestigationState)
    graph.add_node("form_hypothesis", make_form_hypothesis_node())
    graph.add_node("inspect_file", make_inspect_file_node(sandbox))
    graph.add_node("check_history", make_check_history_node(sandbox))

    graph.set_entry_point("form_hypothesis")
    graph.add_conditional_edges(
        "form_hypothesis",
        should_continue,
        {"inspect_file": "inspect_file", "check_history": "check_history", "end": END},
    )
    graph.add_edge("inspect_file", "form_hypothesis")
    graph.add_edge("check_history", "form_hypothesis")

    return graph.compile()
