import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.code_analysis import build_repository_map
from app.core.cost_tracker import RunCostTracker
from app.core.implementer import ImplementationState, build_implementation_graph
from app.core.investigator import InvestigationState, build_investigator_graph
from app.core.mentor import MentorState, build_mentor_resume_graph, build_mentor_start_graph
from app.core.sandbox import SandboxManager, get_sandbox_manager

router = APIRouter(prefix="/sandboxes", tags=["sandboxes"])


class CreateSandboxRequest(BaseModel):
    repo_clone_url: str


class RunCommandRequest(BaseModel):
    command: str


class InvestigateRequest(BaseModel):
    issue_title: str
    issue_body: str


class ImplementRequest(BaseModel):
    target_file: str
    issue_title: str
    issue_body: str
    test_command: str
    skill_context: str = ""


class StartMentorRequest(BaseModel):
    issue_title: str
    issue_body: str
    target_file: str
    original_content: str
    test_command: str
    proficiency: str  # "beginner" | "intermediate" | "advanced"


class SubmitAttemptRequest(BaseModel):
    human_attempt: str


@router.post("")
async def create_sandbox(
    payload: CreateSandboxRequest,
    manager: Annotated[SandboxManager, Depends(get_sandbox_manager)],
) -> dict[str, Any]:
    sandbox = manager.create(payload.repo_clone_url)
    return {"workspace_id": str(sandbox.workspace_id)}


@router.post("/{workspace_id}/run")
async def run_command(
    workspace_id: uuid.UUID,
    payload: RunCommandRequest,
    manager: Annotated[SandboxManager, Depends(get_sandbox_manager)],
) -> dict[str, Any]:
    sandbox = manager.get(workspace_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    exit_code, output = sandbox.run(payload.command)
    return {"exit_code": exit_code, "output": output}


@router.delete("/{workspace_id}")
async def destroy_sandbox(
    workspace_id: uuid.UUID,
    manager: Annotated[SandboxManager, Depends(get_sandbox_manager)],
) -> dict[str, str]:
    manager.destroy(workspace_id)
    return {"status": "destroyed"}


@router.get("/{workspace_id}/repo-map")
async def get_repo_map(
    workspace_id: uuid.UUID,
    manager: Annotated[SandboxManager, Depends(get_sandbox_manager)],
) -> dict[str, Any]:
    sandbox = manager.get(workspace_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    repo_map = build_repository_map(sandbox)
    return {
        "file_count": len(repo_map.files),
        "summary": repo_map.summary(),
    }


@router.post("/{workspace_id}/investigate")
async def investigate(
    workspace_id: uuid.UUID,
    payload: InvestigateRequest,
    manager: Annotated[SandboxManager, Depends(get_sandbox_manager)],
) -> dict[str, Any]:
    sandbox = manager.get(workspace_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    repo_map = build_repository_map(sandbox)
    graph = build_investigator_graph(sandbox)

    initial_state: InvestigationState = {
        "issue_title": payload.issue_title,
        "issue_body": payload.issue_body,
        "repo_map_summary": repo_map.summary(),
        "inspected_files": {},
        "hypothesis": "",
        "target_file": "",
        "confidence": 0.0,
        "iteration": 0,
        "history": [],
        "file_histories": {},
        "check_history": False,
    }

    result = graph.invoke(initial_state)

    return {
        "hypothesis": result["hypothesis"],
        "target_file": result["target_file"],
        "confidence": result["confidence"],
        "iterations": result["iteration"],
        "files_inspected": list(result["inspected_files"].keys()),
    }


@router.post("/{workspace_id}/implement")
async def implement(
    workspace_id: uuid.UUID,
    payload: ImplementRequest,
    manager: Annotated[SandboxManager, Depends(get_sandbox_manager)],
) -> dict[str, Any]:
    sandbox = manager.get(workspace_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    original_content = sandbox.read_file(f"/workspace/repo/{payload.target_file}") or ""

    cost_tracker = RunCostTracker()
    graph = build_implementation_graph(sandbox, cost_tracker)

    initial_state: ImplementationState = {
        "issue_title": payload.issue_title,
        "issue_body": payload.issue_body,
        "target_file": payload.target_file,
        "original_content": original_content,
        "current_content": original_content,
        "test_command": payload.test_command,
        "test_output": "",
        "tests_passed": False,
        "teaching_summary": "",
        "iteration": 0,
        "history": [],
        "skill_context": payload.skill_context,
    }

    result = graph.invoke(initial_state)

    return {
        "tests_passed": result["tests_passed"],
        "iteration": result["iteration"],
        "teaching_summary": result["teaching_summary"],
        "current_content": result["current_content"],
    }


@router.post("/{workspace_id}/mentor/start")
async def start_mentoring(
    workspace_id: uuid.UUID,
    payload: StartMentorRequest,
    manager: Annotated[SandboxManager, Depends(get_sandbox_manager)],
) -> dict[str, Any]:
    sandbox = manager.get(workspace_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    cost_tracker = RunCostTracker()
    graph = build_mentor_start_graph(sandbox, cost_tracker)

    initial_state: MentorState = {
        "issue_title": payload.issue_title,
        "issue_body": payload.issue_body,
        "target_file": payload.target_file,
        "original_content": payload.original_content,
        "reference_solution": "",
        "human_attempt": "",
        "test_command": payload.test_command,
        "test_output": "",
        "tests_passed": False,
        "proficiency": payload.proficiency,
        "hint_count": 0,
        "hints_given": [],
    }

    result = graph.invoke(initial_state)

    session_id = uuid.uuid4()
    result_with_workspace = dict(result)
    result_with_workspace["_workspace_id"] = str(workspace_id)
    manager.save_mentor_session(session_id, result_with_workspace)

    return {
        "session_id": str(session_id),
        "hint": result["hints_given"][-1] if result["hints_given"] else None,
        "hint_count": result["hint_count"],
    }


@router.post("/mentor/{session_id}/submit-attempt")
async def submit_mentor_attempt(
    session_id: uuid.UUID,
    payload: SubmitAttemptRequest,
    manager: Annotated[SandboxManager, Depends(get_sandbox_manager)],
) -> dict[str, Any]:
    session = manager.get_mentor_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Mentor session not found")

    workspace_id = uuid.UUID(session["_workspace_id"])
    sandbox = manager.get(workspace_id)
    if sandbox is None:
        raise HTTPException(status_code=404, detail="Underlying sandbox no longer exists")

    # No RunCostTracker/generate_reference here — the reference solution
    # was already computed once in /mentor/start and is carried through
    # from session state below, so this resume graph starts straight at
    # evaluate_attempt and never re-runs the Implementer graph.
    graph = build_mentor_resume_graph(sandbox)

    state: MentorState = {
        "issue_title": session["issue_title"],
        "issue_body": session["issue_body"],
        "target_file": session["target_file"],
        "original_content": session["original_content"],
        "reference_solution": session["reference_solution"],
        "human_attempt": payload.human_attempt,
        "test_command": session["test_command"],
        "test_output": "",
        "tests_passed": False,
        "proficiency": session["proficiency"],
        "hint_count": session["hint_count"],
        "hints_given": session["hints_given"],
    }

    result = graph.invoke(state)

    result_with_workspace = dict(result)
    result_with_workspace["_workspace_id"] = str(workspace_id)
    manager.save_mentor_session(session_id, result_with_workspace)

    return {
        "tests_passed": result["tests_passed"],
        "test_output": result["test_output"],
        "hint": result["hints_given"][-1] if result["hints_given"] else None,
        "hint_count": result["hint_count"],
    }
