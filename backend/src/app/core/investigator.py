from typing import Any, TypedDict, cast

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.llm_router import ModelTier, get_llm
from app.core.sandbox import Sandbox

CONFIDENCE_THRESHOLD = 0.75
MAX_ITERATIONS = 5


class Hypothesis(BaseModel):
    """The exact shape we force the LLM's response into. Instead of
    parsing free text, LangChain makes the model return JSON matching
    this schema — reliable, no string-parsing guesswork.
    """

    reasoning: str = Field(description="Brief explanation of your current thinking")
    target_file: str = Field(description="The single file path most likely to contain the bug")
    confidence: float = Field(description="0.0 to 1.0 — how confident you are this is correct")


class InvestigationState(TypedDict):
    issue_title: str
    issue_body: str
    repo_map_summary: str
    inspected_files: dict[str, str]  # path -> content, grows each loop
    hypothesis: str
    target_file: str
    confidence: float
    iteration: int
    history: list[str]


def make_form_hypothesis_node() -> Any:
    llm = get_llm(ModelTier.CAPABLE, max_tokens=4096)
    structured_llm = llm.with_structured_output(Hypothesis)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def invoke_with_retry(prompt: str) -> Hypothesis:
        return cast(Hypothesis, structured_llm.invoke(prompt))

    def form_hypothesis(state: InvestigationState) -> dict[str, Any]:
        inspected_summary = "\n\n".join(
            f"--- {path} ---\n{content[:3000]}"
            for path, content in state["inspected_files"].items()
        )

        prompt = f"""You are investigating a bug report to find where it likely originates.

ISSUE: {state["issue_title"]}
{state["issue_body"]}

REPOSITORY MAP:
{state["repo_map_summary"]}

FILES ALREADY INSPECTED:
{inspected_summary if inspected_summary else "(none yet)"}

Based on everything above, form your best hypothesis: which file is most likely
to contain the bug, and how confident are you? If you've already inspected the
right file and are confident, say so. If not, name a NEW file to inspect next.

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


def should_continue(state: InvestigationState) -> str:
    # Never allow ending on iteration 1 — force at least one real file
    # inspection before we trust any confidence score. A confidence
    # number the model asserts without having looked at actual code
    # is not evidence, it's just more unverified text.
    if state["iteration"] < 1 or not state["inspected_files"]:
        return "inspect_file"
    if state["confidence"] >= CONFIDENCE_THRESHOLD:
        return "end"
    if state["iteration"] >= MAX_ITERATIONS:
        return "end"
    return "inspect_file"


def build_investigator_graph(sandbox: Sandbox) -> Any:
    graph = StateGraph(InvestigationState)
    graph.add_node("form_hypothesis", make_form_hypothesis_node())
    graph.add_node("inspect_file", make_inspect_file_node(sandbox))

    graph.set_entry_point("form_hypothesis")
    graph.add_conditional_edges(
        "form_hypothesis", should_continue, {"inspect_file": "inspect_file", "end": END}
    )
    graph.add_edge("inspect_file", "form_hypothesis")

    return graph.compile()
