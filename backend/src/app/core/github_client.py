from typing import Any

import httpx

from app.core.config import get_settings

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def search_repositories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        response = await self._client.get(
            "/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": limit},
        )
        response.raise_for_status()
        items: list[dict[str, Any]] = response.json()["items"]
        return items

    async def list_open_issues(self, full_name: str, limit: int = 20) -> list[dict[str, Any]]:
        response = await self._client.get(
            f"/repos/{full_name}/issues",
            params={"state": "open", "per_page": limit},
        )
        response.raise_for_status()
        data: list[dict[str, Any]] = response.json()
        return [item for item in data if "pull_request" not in item]

    async def close(self) -> None:
        await self._client.aclose()

    async def create_branch(
        self, full_name: str, branch_name: str, base_branch: str = "main"
    ) -> None:
        base_ref = await self._client.get(f"/repos/{full_name}/git/ref/heads/{base_branch}")
        base_ref.raise_for_status()
        base_sha = base_ref.json()["object"]["sha"]

        response = await self._client.post(
            f"/repos/{full_name}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )
        response.raise_for_status()

    async def create_pull_request(
        self, full_name: str, title: str, body: str, head_branch: str, base_branch: str = "main"
    ) -> dict[str, Any]:
        response = await self._client.post(
            f"/repos/{full_name}/pulls",
            json={"title": title, "body": body, "head": head_branch, "base": base_branch},
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def get_pull_request_status(self, full_name: str, pr_number: int) -> dict[str, Any]:
        response = await self._client.get(f"/repos/{full_name}/pulls/{pr_number}")
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def list_pull_request_comments(
        self, full_name: str, pr_number: int
    ) -> list[dict[str, Any]]:
        response = await self._client.get(f"/repos/{full_name}/issues/{pr_number}/comments")
        response.raise_for_status()
        result: list[dict[str, Any]] = response.json()
        return result

    async def create_or_update_file(
        self, full_name: str, path: str, content: str, message: str, branch: str
    ) -> None:
        import base64

        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        response = await self._client.put(
            f"/repos/{full_name}/contents/{path}",
            json={"message": message, "content": encoded_content, "branch": branch},
        )
        response.raise_for_status()


def get_github_client() -> GitHubClient:
    settings = get_settings()
    return GitHubClient(token=settings.github_write_token)
