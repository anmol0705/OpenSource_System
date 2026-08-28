import uuid
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.core.pr_manager import PRManagerState, build_pr_manager_graph
from app.core.sandbox import get_sandbox_manager
from app.main import app


def make_fake_sandbox() -> MagicMock:
    return MagicMock()


def make_fake_github() -> MagicMock:
    github = MagicMock()
    github.create_pull_request = AsyncMock()
    return github


def make_state(human_approved: bool = False) -> PRManagerState:
    return {
        "repo_full_name": "octocat/hello-world",
        "branch_name": "fix/off-by-one",
        "target_file": "app.py",
        "final_content": "def foo(): return 2",
        "commit_message": "Fix off-by-one bug",
        "pr_title": "Fix off-by-one bug",
        "pr_body": "Fixes the reported issue.",
        "pr_number": None,
        "status": "",
        "human_approved": human_approved,
        "latest_comments": [],
        "test_command": "pytest",
        "issue_title": "off-by-one bug",
        "issue_body": "foo() returns the wrong value",
    }


async def test_first_invocation_without_approval_awaits_human_and_never_pushes() -> None:
    sandbox = make_fake_sandbox()
    github = make_fake_github()
    graph = build_pr_manager_graph(sandbox, github)

    result = await graph.ainvoke(make_state(human_approved=False))

    assert result["status"] == "awaiting_human_approval"
    sandbox.run.assert_not_called()
    github.create_pull_request.assert_not_called()


async def test_approved_invocation_pushes_and_creates_pr() -> None:
    sandbox = make_fake_sandbox()
    sandbox.run.return_value = (0, "success output")
    github = make_fake_github()
    github.create_pull_request.return_value = {"number": 42}
    graph = build_pr_manager_graph(sandbox, github)

    result = await graph.ainvoke(make_state(human_approved=True))

    assert result["status"] == "pushed"
    assert result["pr_number"] == 42
    github.create_pull_request.assert_awaited_once()


async def test_failed_push_never_attempts_to_create_pr() -> None:
    sandbox = make_fake_sandbox()
    sandbox.run.return_value = (1, "fatal: could not push")
    github = make_fake_github()
    graph = build_pr_manager_graph(sandbox, github)

    result = await graph.ainvoke(make_state(human_approved=True))

    assert result["status"] == "push_failed"
    github.create_pull_request.assert_not_called()


async def test_approve_endpoint_unknown_session_returns_404() -> None:
    fake_manager = MagicMock()
    fake_manager.get_mentor_session.return_value = None
    app.dependency_overrides[get_sandbox_manager] = lambda: fake_manager
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/sandboxes/pr/{uuid.uuid4()}/approve")
        assert response.status_code == 404
        assert response.json()["detail"] == "PR session not found"
    finally:
        app.dependency_overrides.pop(get_sandbox_manager, None)


async def test_approve_endpoint_missing_sandbox_returns_distinct_404() -> None:
    fake_manager = MagicMock()
    fake_manager.get_mentor_session.return_value = {
        "_workspace_id": str(uuid.uuid4()),
        "repo_full_name": "octocat/hello-world",
        "branch_name": "fix/off-by-one",
        "target_file": "app.py",
        "final_content": "def foo(): return 2",
        "commit_message": "Fix off-by-one bug",
        "pr_title": "Fix off-by-one bug",
        "pr_body": "Fixes the reported issue.",
        "pr_number": None,
        "status": "awaiting_human_approval",
        "latest_comments": [],
        "test_command": "pytest",
        "issue_title": "off-by-one bug",
        "issue_body": "foo() returns the wrong value",
    }
    fake_manager.get.return_value = None
    app.dependency_overrides[get_sandbox_manager] = lambda: fake_manager
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/sandboxes/pr/{uuid.uuid4()}/approve")
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail == "Underlying sandbox no longer exists"
        assert detail != "PR session not found"
    finally:
        app.dependency_overrides.pop(get_sandbox_manager, None)
