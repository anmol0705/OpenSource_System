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


def get_github_client() -> GitHubClient:
    settings = get_settings()
    return GitHubClient(token=settings.github_token)
