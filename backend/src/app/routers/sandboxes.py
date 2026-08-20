import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.sandbox import SandboxManager, get_sandbox_manager

router = APIRouter(prefix="/sandboxes", tags=["sandboxes"])


class CreateSandboxRequest(BaseModel):
    repo_clone_url: str


class RunCommandRequest(BaseModel):
    command: str


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
