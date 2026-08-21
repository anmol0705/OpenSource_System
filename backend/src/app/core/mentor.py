from typing import Any, TypedDict, cast

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.cost_tracker import RunCostTracker
from app.core.implementer import build_implementation_graph
from app.core.llm_router import ModelTier, get_llm
from app.core.sandbox import Sandbox
from app.core.settings_tuning import ALLOWED_TEST_COMMANDS

MAX_HINTS = 4

HINT_STYLE_BY_PROFICIENCY = {
    "beginner": "Be generous — point at the specific area and concept, but never write "
    "code for them.",
    "intermediate": "Point at the general area only; make them figure out the specific "
    "mechanism.",
    "advanced": "Ask a single probing question; assume they can find the area themselves.",
}


class Hint(BaseModel):
    hint_text: str = Field(
        description="A Socratic nudge toward the fix — a question or pointer, NEVER the "
        "actual code or the exact fix. Calibrated by the requested hint style."
    )
    reveals_solution: bool = Field(
        default=False, description="True only if this is the final forced reveal after max hints."
    )


class MentorState(TypedDict):
    issue_title: str
    issue_body: str
    target_file: str
    original_content: str
    reference_solution: str  # hidden from the human, used only to inform hints
    human_attempt: str  # what the human actually wrote
    test_command: str
    test_output: str
    tests_passed: bool
    proficiency: str  # "beginner" | "intermediate" | "advanced"
    hint_count: int
    hints_given: list[str]


def make_generate_reference_node(sandbox: Sandbox, cost_tracker: RunCostTracker) -> Any:
    """Runs the Phase 6 Implementer graph internally, once, to get a working
    reference fix — never surfaced to the human, only used to make hints
    actually informed instead of generic.
    """
    impl_graph = build_implementation_graph(sandbox, cost_tracker)

    def generate_reference(state: MentorState) -> dict[str, Any]:
        result = impl_graph.invoke(
            {
                "issue_title": state["issue_title"],
                "issue_body": state["issue_body"],
                "target_file": state["target_file"],
                "original_content": state["original_content"],
                "current_content": state["original_content"],
                "test_command": state["test_command"],
                "test_output": "",
                "tests_passed": False,
                "teaching_summary": "",
                "iteration": 0,
                "history": [],
                "skill_context": "",
            }
        )
        return {"reference_solution": result["current_content"]}

    return generate_reference


def make_generate_hint_node() -> Any:
    llm = get_llm(ModelTier.CAPABLE, max_tokens=1024)
    structured_llm = llm.with_structured_output(Hint)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def invoke_with_retry(prompt: str) -> Hint:
        return cast(Hint, structured_llm.invoke(prompt))

    def generate_hint(state: MentorState) -> dict[str, Any]:
        style = HINT_STYLE_BY_PROFICIENCY.get(
            state["proficiency"], HINT_STYLE_BY_PROFICIENCY["intermediate"]
        )
        force_reveal = state["hint_count"] >= MAX_HINTS

        attempt_context = (
            f"\n\nTHEIR LATEST ATTEMPT:\n{state['human_attempt']}\n\n"
            f"TEST OUTPUT FROM THAT ATTEMPT:\n{state['test_output']}"
            if state["human_attempt"]
            else "\n\n(They have not attempted a fix yet — this is the first hint.)"
        )

        reveal_instruction = (
            "\nThe human has used all their hints and is stuck. Set reveals_solution=true "
            "and this time explain the reference fix directly, with full reasoning — this "
            "is the safety-valve reveal, not a hint."
            if force_reveal
            else "\nDo NOT reveal the fix. reveals_solution must be false."
        )

        prompt = f"""You are mentoring a developer fixing a real bug, Socratic-style — like a
good technical interviewer who guides without giving away the answer.

ISSUE: {state["issue_title"]}
{state["issue_body"]}

FILE: {state["target_file"]}
{state["original_content"]}

REFERENCE FIX (never show this to them directly, only use it to judge their
progress and inform your hint):
{state["reference_solution"]}
{attempt_context}

HINT STYLE FOR THIS DEVELOPER'S LEVEL ({state["proficiency"]}): {style}
{reveal_instruction}

Give ONE hint — a question or pointer that moves their thinking forward without
writing the fix for them."""

        result = invoke_with_retry(prompt)
        next_count = state["hint_count"] + 1

        return {
            "hint_count": next_count,
            "hints_given": state["hints_given"] + [result.hint_text],
        }

    return generate_hint


def make_evaluate_attempt_node(sandbox: Sandbox) -> Any:
    def evaluate_attempt(state: MentorState) -> dict[str, Any]:
        if state["test_command"] not in ALLOWED_TEST_COMMANDS:
            return {"tests_passed": False, "test_output": "Refused: disallowed test command"}
        if not state["human_attempt"]:
            return {"tests_passed": False, "test_output": ""}

        full_path = f"/workspace/repo/{state['target_file']}"
        sandbox.write_file(full_path, state["human_attempt"])
        passed, output = sandbox.run_tests(state["test_command"])

        return {"tests_passed": passed, "test_output": output}

    return evaluate_attempt


def should_continue_mentoring(state: MentorState) -> str:
    if state["tests_passed"]:
        return "end"
    if state["hint_count"] > MAX_HINTS:  # one extra pass already delivered the forced reveal
        return "end"
    return "generate_hint"


def build_mentor_start_graph(sandbox: Sandbox, cost_tracker: RunCostTracker) -> Any:
    graph = StateGraph(MentorState)
    graph.add_node("generate_reference", make_generate_reference_node(sandbox, cost_tracker))
    graph.add_node("evaluate_attempt", make_evaluate_attempt_node(sandbox))
    graph.add_node("generate_hint", make_generate_hint_node())

    graph.set_entry_point("generate_reference")
    graph.add_edge("generate_reference", "evaluate_attempt")
    graph.add_conditional_edges(
        "evaluate_attempt",
        should_continue_mentoring,
        {"generate_hint": "generate_hint", "end": END},
    )
    graph.add_edge("generate_hint", END)  # one hint per real invocation — see note below

    return graph.compile()


def build_mentor_resume_graph(sandbox: Sandbox) -> Any:
    """For every call AFTER /mentor/start — the reference solution was
    already computed once and lives in the session state, so this graph
    starts at evaluate_attempt instead of generate_reference. Re-running
    generate_reference here would silently re-invoke the entire Implementer
    graph (and its own LLM calls) on every single hint request, which is
    both wasted spend and a correctness bug: the "reference" the mentor is
    judging against could drift between attempts within the same session.
    """
    graph = StateGraph(MentorState)
    graph.add_node("evaluate_attempt", make_evaluate_attempt_node(sandbox))
    graph.add_node("generate_hint", make_generate_hint_node())

    graph.set_entry_point("evaluate_attempt")
    graph.add_conditional_edges(
        "evaluate_attempt",
        should_continue_mentoring,
        {"generate_hint": "generate_hint", "end": END},
    )
    graph.add_edge("generate_hint", END)

    return graph.compile()
