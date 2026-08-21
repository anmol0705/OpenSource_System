from typing import Any, TypedDict, cast

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.cost_tracker import RunCostTracker
from app.core.llm_router import ModelTier, get_llm
from app.core.sandbox import Sandbox
from app.core.settings_tuning import ALLOWED_TEST_COMMANDS, MAX_IMPLEMENTATION_ITERATIONS


class Patch(BaseModel):
    """What we force the LLM to return when asked to write/revise code.
    Whole-file replacement, not a diff — see the V1 simplification note.
    """

    explanation: str = Field(description="Brief explanation of what you changed and why")
    new_file_content: str = Field(description="The COMPLETE new content of the file, not a diff")
    teaching_summary: str = Field(
        description="A short, plain-English lesson for a developer learning from this fix: "
        "what KIND of bug this was (e.g. 'off-by-one', 'not decoding gzip before use'), why "
        "the fix works, and what to watch for to avoid this class of bug in the future. "
        "Written for someone trying to learn, not just told what happened."
    )


class ImplementationState(TypedDict):
    issue_title: str
    issue_body: str
    target_file: str
    original_content: str
    current_content: str
    test_command: str
    test_output: str
    tests_passed: bool
    teaching_summary: str
    iteration: int
    history: list[str]
    skill_context: str


def _is_safe_target_file(path: str) -> bool:
    """Rejects path traversal and any attempt to write outside the cloned
    repo or into .git — this must degrade to False, never raise, so the
    caller can fold it into the normal failed-test iteration path instead
    of crashing the whole run.
    """
    if ".." in path:
        return False
    if path.startswith("/") and not path.startswith("/workspace/repo"):
        return False
    return ".git/" not in path and not path.startswith(".git/")


def make_generate_patch_node(cost_tracker: RunCostTracker) -> Any:
    max_tokens = 4096
    llm = get_llm(ModelTier.CAPABLE, max_tokens=max_tokens)
    structured_llm = llm.with_structured_output(Patch, include_raw=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def invoke_with_retry(prompt: str) -> dict[str, Any]:
        cost_tracker.check_before_call(
            estimated_input_tokens=len(prompt) // 4,
            estimated_output_tokens=max_tokens,
        )
        result = cast(dict[str, Any], structured_llm.invoke(prompt))

        raw = result.get("raw")
        usage = getattr(raw, "usage_metadata", None) if raw is not None else None
        if usage:
            cost_tracker.record_usage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
            )

        return result

    def generate_patch(state: ImplementationState) -> dict[str, Any]:
        test_feedback = (
            f"\n\nPREVIOUS ATTEMPT FAILED TESTS. Use this as concrete evidence of what's "
            f"actually wrong rather than guessing again — read it carefully:\n"
            f"{state['test_output']}"
            if state["test_output"]
            else ""
        )

        prompt = f"""You are fixing a bug in {state["target_file"]}, for a developer who is
learning from this fix, not just requesting an autonomous patch.

ISSUE: {state["issue_title"]}
{state["issue_body"]}

CURRENT FILE CONTENT:
{state["current_content"]}
{test_feedback}

DEVELOPER SKILL CONTEXT (for calibrating your teaching_summary):
{state["skill_context"]}

Write the COMPLETE new content of this file with the bug fixed. Make the
smallest change that correctly fixes the issue — do not refactor unrelated
code, do not change formatting of code you didn't need to touch. If tests
failed previously, carefully read the failure output above and fix the
actual cause it points to, don't just guess randomly.

Also write a short teaching_summary: explain the general CLASS of bug this
is and why the fix works, so a developer reading this later actually learns
something transferable, not just "here's a diff." Use the developer skill
context above only to calibrate how much you need to explain vs. how much
you can assume — e.g. skip basics they've clearly already got, spell out
concepts they haven't encountered yet. Do not state or imply any judgment
about the developer's competence or skill level anywhere in your response;
adjust depth silently, the way a good mentor does."""

        result = invoke_with_retry(prompt)
        patch = cast(Patch, result["parsed"])
        next_iteration = state["iteration"] + 1

        return {
            "current_content": patch.new_file_content,
            "teaching_summary": patch.teaching_summary,
            "iteration": next_iteration,
            "history": state["history"] + [f"iteration {next_iteration}: {patch.explanation}"],
        }

    return generate_patch


def make_apply_and_test_node(sandbox: Sandbox) -> Any:
    def apply_and_test(state: ImplementationState) -> dict[str, Any]:
        target_file = state["target_file"]
        if not _is_safe_target_file(target_file):
            return {
                "tests_passed": False,
                "test_output": f"Refused to write to disallowed path: {target_file!r}",
            }

        test_command = state["test_command"]
        if test_command not in ALLOWED_TEST_COMMANDS:
            return {
                "tests_passed": False,
                "test_output": f"Refused to run disallowed test command: {test_command!r}",
            }

        full_path = f"/workspace/repo/{target_file}"
        sandbox.write_file(full_path, state["current_content"])

        passed, output = sandbox.run_tests(test_command)

        return {"tests_passed": passed, "test_output": output}

    return apply_and_test


def should_continue_implementation(state: ImplementationState) -> str:
    if state["iteration"] < 1:
        return "apply_and_test"
    if state["tests_passed"]:
        return "end"
    if state["iteration"] >= MAX_IMPLEMENTATION_ITERATIONS:
        return "end"
    return "generate_patch"


def build_implementation_graph(sandbox: Sandbox, cost_tracker: RunCostTracker) -> Any:
    graph = StateGraph(ImplementationState)
    graph.add_node("generate_patch", make_generate_patch_node(cost_tracker))
    graph.add_node("apply_and_test", make_apply_and_test_node(sandbox))

    graph.set_entry_point("generate_patch")
    graph.add_edge("generate_patch", "apply_and_test")
    graph.add_conditional_edges(
        "apply_and_test",
        should_continue_implementation,
        {"generate_patch": "generate_patch", "end": END},
    )

    return graph.compile()
