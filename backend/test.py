import asyncio

from app.core.github_client import get_github_client


async def main():
    client = get_github_client()

    repo = "anmol0705/apprentice-test-sandbox"

    await client.create_branch(repo, "test-branch-2")
    print("branch created")

    await client.create_or_update_file(
        repo,
        path="test-file.md",
        content="# Test\n\nThis file was created by the PR Manager test script.",
        message="Add test file",
        branch="test-branch-2",
    )
    print("file committed")

    pr = await client.create_pull_request(
        repo,
        title="Test PR from apprentice system",
        body="This is a test PR created by the PR Manager code, not a real change.",
        head_branch="test-branch-2",
    )
    print("PR created:", pr["html_url"])

    await client.close()


asyncio.run(main())
