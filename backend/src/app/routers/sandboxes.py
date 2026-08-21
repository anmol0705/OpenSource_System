import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.code_analysis import build_repository_map
from app.core.investigator import InvestigationState, build_investigator_graph
from app.core.sandbox import SandboxManager, get_sandbox_manager

router = APIRouter(prefix="/sandboxes", tags=["sandboxes"])


class CreateSandboxRequest(BaseModel):
    repo_clone_url: str


class RunCommandRequest(BaseModel):
    command: str


class InvestigateRequest(BaseModel):
    issue_title: str
    issue_body: str


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
