import shutil
import tempfile
import uuid
from pathlib import Path

import docker
from docker.models.containers import Container

SANDBOX_IMAGE = "apprentice-sandbox:latest"


class Sandbox:
    """One isolated workspace for one contribution attempt.

    Everything happens inside a single Docker container with the target
    repo mounted in — no access to the host filesystem beyond that one
    mounted folder, and the container is destroyed when we're done.
    """

    def __init__(self, workspace_id: uuid.UUID, host_workspace_path: Path, container: Container):
        self.workspace_id = workspace_id
        self.host_workspace_path = host_workspace_path
        self.container = container

    def run(self, command: str, workdir: str = "/workspace/repo") -> tuple[int, str]:
        """Run a shell command INSIDE the container, not on the host.
        Returns (exit_code, combined_stdout_and_stderr).
        """
        exit_code, output = self.container.exec_run(
            cmd=["sh", "-c", command],
            workdir=workdir,
        )
        return exit_code, output.decode("utf-8", errors="replace")

    def destroy(self) -> None:
        """Tear down the container AND wipe the host-side workspace folder.
        Called once we're done with this contribution attempt — nothing
        about it should linger on disk or as a running container.
        """
        self.container.stop(timeout=5)
        self.container.remove()
        shutil.rmtree(self.host_workspace_path, ignore_errors=True)

    def read_file(self, path: str) -> str | None:
        """Read a file's contents from inside the sandbox. Returns None
        if the file doesn't exist, rather than raising — a missing file
        is an expected, normal outcome an agent needs to handle, not
        an exceptional one.
        """
        exit_code, output = self.run(f"cat {path!r}")
        if exit_code != 0:
            return None
        return output

    def write_file(self, path: str, content: str) -> None:
        """Write content to a file inside the sandbox. Uses a heredoc
        rather than passing content as a shell argument, so file content
        containing quotes/special characters doesn't break the command.
        """
        marker = "APPRENTICE_EOF"
        command = f"cat > {path!r} << '{marker}'\n{content}\n{marker}"
        exit_code, output = self.run(command)
        if exit_code != 0:
            raise RuntimeError(f"write_file failed for {path}: {output}")

    def run_tests(self, test_command: str = "python -m pytest") -> tuple[bool, str]:
        """Run the repo's test suite inside the sandbox. Returns
        (passed, output) — passed is a simple bool an agent can branch
        on without needing to know exit-code conventions.
        """
        exit_code, output = self.run(test_command)
        return exit_code == 0, output

    def list_source_files(self, extensions: list[str] | None = None) -> list[str]:
        """List source files in the repo, respecting .gitignore automatically
        (ripgrep does this by default — that's part of why we use it over
        a naive `find`, which would happily list node_modules, venv, etc.)
        """
        if extensions is None:
            extensions = ["py", "js", "ts", "jsx", "tsx"]

        type_flags = " ".join(f"-g '*.{ext}'" for ext in extensions)
        exit_code, output = self.run(f"rg --files {type_flags}", workdir="/workspace/repo")

        if exit_code != 0:
            return []
        return [line for line in output.strip().split("\n") if line]


class SandboxManager:
    """Creates and tracks isolated Sandbox instances. This is the ONLY
    place in the codebase that's allowed to talk to the Docker SDK directly
    — every other part of the app goes through this class, never docker.py
    directly. That's what makes sandboxing an enforced boundary, not just
    a convention people can accidentally bypass.
    """

    def __init__(self) -> None:
        self._client = docker.from_env()
        # In-memory registry: workspace_id -> Sandbox. Lost on server
        # restart — acceptable for now (Phase 2). Phase 4 will need to
        # persist workspace state properly once the agent has real
        # investigation state to track across a longer-running session.
        self._active_sandboxes: dict[uuid.UUID, Sandbox] = {}

    def create(self, repo_clone_url: str) -> Sandbox:
        workspace_id = uuid.uuid4()

        host_path = Path(tempfile.gettempdir()) / "apprentice-workspaces" / str(workspace_id)
        host_path.mkdir(parents=True, exist_ok=True)

        container = self._client.containers.run(
            image=SANDBOX_IMAGE,
            command="sleep infinity",  # keep it alive; we run commands into it via exec
            detach=True,
            volumes={str(host_path): {"bind": "/workspace", "mode": "rw"}},
            network_mode="bridge",  # needed for git clone; we'll restrict this further later
            mem_limit="1g",
            nano_cpus=1_000_000_000,  # limit to 1 CPU core
        )

        sandbox = Sandbox(workspace_id, host_path, container)

        clone_exit, clone_output = sandbox.run(
            f"git clone --depth 1 {repo_clone_url} /workspace/repo", workdir="/workspace"
        )
        if clone_exit != 0:
            sandbox.destroy()
            raise RuntimeError(f"git clone failed: {clone_output}")

        self._active_sandboxes[workspace_id] = sandbox
        return sandbox

    def get(self, workspace_id: uuid.UUID) -> Sandbox | None:
        return self._active_sandboxes.get(workspace_id)

    def destroy(self, workspace_id: uuid.UUID) -> None:
        sandbox = self._active_sandboxes.pop(workspace_id, None)
        if sandbox:
            sandbox.destroy()


_manager_instance: SandboxManager | None = None


def get_sandbox_manager() -> SandboxManager:
    """Same shared-instance goal as get_settings()'s @lru_cache, but
    written explicitly here since we're intentionally holding shared
    MUTABLE state (the sandbox registry) across requests — worth being
    obvious about that in the code, not hidden behind a decorator.
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SandboxManager()
    return _manager_instance
