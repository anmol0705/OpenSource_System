import uuid
from unittest.mock import MagicMock, patch

from app.core.sandbox import SandboxManager


def make_fake_container(exec_responses: dict[str, tuple[int, bytes]]) -> MagicMock:
    """Builds a fake Docker container whose exec_run() returns canned
    responses based on the command it was given — lets us simulate
    'git clone succeeded' or 'git clone failed' without real Docker.
    """
    container = MagicMock()

    def fake_exec_run(cmd: list[str], workdir: str) -> tuple[int, bytes]:
        command_str = cmd[-1]  # cmd is ["sh", "-c", "<actual command>"]
        for key, response in exec_responses.items():
            if key in command_str:
                return response
        return (0, b"")

    container.exec_run.side_effect = fake_exec_run
    return container


@patch("app.core.sandbox.docker.from_env")
def test_create_sandbox_clones_repo_successfully(mock_from_env: MagicMock) -> None:
    fake_container = make_fake_container({"git clone": (0, b"Cloning into 'repo'...")})
    mock_docker_client = MagicMock()
    mock_docker_client.containers.run.return_value = fake_container
    mock_from_env.return_value = mock_docker_client

    manager = SandboxManager()
    sandbox = manager.create("https://github.com/example/repo.git")

    assert sandbox.workspace_id is not None
    mock_docker_client.containers.run.assert_called_once()
    # Confirm the clone command actually contains the URL we asked for —
    # catches typos/bugs in how we build the git clone command.
    fake_container.exec_run.assert_any_call(
        cmd=["sh", "-c", "git clone https://github.com/example/repo.git /workspace/repo"],
        workdir="/workspace",
    )


@patch("app.core.sandbox.docker.from_env")
def test_create_sandbox_cleans_up_on_clone_failure(mock_from_env: MagicMock) -> None:
    fake_container = make_fake_container({"git clone": (128, b"fatal: repository not found")})
    mock_docker_client = MagicMock()
    mock_docker_client.containers.run.return_value = fake_container
    mock_from_env.return_value = mock_docker_client

    manager = SandboxManager()

    try:
        manager.create("https://github.com/example/does-not-exist.git")
        raise AssertionError("expected RuntimeError to be raised")
    except RuntimeError as e:
        assert "git clone failed" in str(e)

    # Even on failure, we should have torn the container down —
    # no orphaned resources left behind.
    fake_container.stop.assert_called_once()
    fake_container.remove.assert_called_once()


@patch("app.core.sandbox.docker.from_env")
def test_get_returns_none_for_unknown_workspace(mock_from_env: MagicMock) -> None:
    mock_from_env.return_value = MagicMock()
    manager = SandboxManager()

    result = manager.get(uuid.uuid4())

    assert result is None


@patch("app.core.sandbox.docker.from_env")
def test_destroy_removes_sandbox_from_registry(mock_from_env: MagicMock) -> None:
    fake_container = make_fake_container({"git clone": (0, b"")})
    mock_docker_client = MagicMock()
    mock_docker_client.containers.run.return_value = fake_container
    mock_from_env.return_value = mock_docker_client

    manager = SandboxManager()
    sandbox = manager.create("https://github.com/example/repo.git")
    workspace_id = sandbox.workspace_id

    manager.destroy(workspace_id)

    assert manager.get(workspace_id) is None
