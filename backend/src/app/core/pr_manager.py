from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.core.github_client import GitHubClient
from app.core.sandbox import Sandbox


class PRManagerState(TypedDict):
    repo_full_name: str
    branch_name: str
    target_file: str
    final_content: str
    commit_message: str
    pr_title: str
    pr_body: str
    pr_number: int | None
    status: str  # "awaiting_human_approval" | "pushed" | "changes_requested" | "merged"
    human_approved: bool
    latest_comments: list[str]
    test_command: str
    issue_title: str
    issue_body: str


def make_await_approval_node() -> Any:
    def await_approval(state: PRManagerState) -> dict[str, Any]:
        # This node deliberately does almost nothing — the graph run ENDS
        # here on the first pass (human_approved starts False). Resuming
        # happens via a separate endpoint call with human_approved=True,
        # not by looping inside one invoke() — same pattern as the Mentor's
        # submit-attempt flow, because a real human decision can't happen
        # synchronously inside a single graph execution.
        if state["human_approved"]:
            return {"status": "approved"}
        return {"status": "awaiting_human_approval"}

    return await_approval


def make_push_and_create_pr_node(sandbox: Sandbox, github: GitHubClient) -> Any:
    async def push_and_create_pr(state: PRManagerState) -> dict[str, Any]:
        sandbox.write_file(f"/workspace/repo/{state['target_file']}", state["final_content"])

        exit_code, output = sandbox.run(
            f"git checkout -b {state['branch_name']} && "
            f"git add {state['target_file']} && "
            f'git -c user.email="agent@apprentice.dev" -c user.name="Apprentice Agent" '
            f'commit -m "{state["commit_message"]}" && '
            f"git push origin {state['branch_name']}"
        )
        if exit_code != 0:
            return {"status": "push_failed"}

        pr = await github.create_pull_request(
            state["repo_full_name"],
            title=state["pr_title"],
            body=state["pr_body"],
            head_branch=state["branch_name"],
        )

        return {"status": "pushed", "pr_number": pr["number"]}

    return push_and_create_pr


def should_proceed_after_approval(state: PRManagerState) -> str:
    if state["human_approved"]:
        return "push_and_create_pr"
    return "end"


def build_pr_manager_graph(sandbox: Sandbox, github: GitHubClient) -> Any:
    graph = StateGraph(PRManagerState)
    graph.add_node("await_approval", make_await_approval_node())
    graph.add_node("push_and_create_pr", make_push_and_create_pr_node(sandbox, github))

    graph.set_entry_point("await_approval")
    graph.add_conditional_edges(
        "await_approval",
        should_proceed_after_approval,
        {"push_and_create_pr": "push_and_create_pr", "end": END},
    )
    graph.add_edge("push_and_create_pr", END)

    return graph.compile()
