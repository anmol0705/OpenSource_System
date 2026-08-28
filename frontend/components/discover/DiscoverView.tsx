"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  createSandbox,
  discoverIssues,
  discoverRepositories,
  type IssueResult,
  type RepoResult,
} from "@/lib/api";
import { loadProfile, saveInvestigationContext } from "@/lib/storage";
import { ScoreBreakdown } from "./ScoreBreakdown";

type AsyncStatus = "idle" | "loading" | "error" | "success";

export function DiscoverView() {
  const router = useRouter();
  const profile = loadProfile();

  const [query, setQuery] = useState("");
  const [repoStatus, setRepoStatus] = useState<AsyncStatus>("idle");
  const [repoError, setRepoError] = useState<string | null>(null);
  const [repos, setRepos] = useState<RepoResult[]>([]);

  const [selectedRepo, setSelectedRepo] = useState<RepoResult | null>(null);
  const [issueStatus, setIssueStatus] = useState<AsyncStatus>("idle");
  const [issueError, setIssueError] = useState<string | null>(null);
  const [issues, setIssues] = useState<IssueResult[]>([]);

  const [sandboxStatus, setSandboxStatus] = useState<AsyncStatus>("idle");
  const [sandboxError, setSandboxError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setRepoStatus("loading");
    setRepoError(null);
    setSelectedRepo(null);
    setIssues([]);
    try {
      const results = await discoverRepositories(query, 10);
      setRepos(results);
      setRepoStatus("success");
    } catch (err) {
      setRepoError(err instanceof ApiError ? err.message : "Repository search failed.");
      setRepoStatus("error");
    }
  }

  async function handleSelectRepo(repo: RepoResult) {
    setSelectedRepo(repo);
    setIssueStatus("loading");
    setIssueError(null);
    setIssues([]);

    if (!profile) {
      setIssueError("No developer profile found. Set up your profile first.");
      setIssueStatus("error");
      return;
    }

    try {
      const results = await discoverIssues(repo.full_name, profile.id);
      setIssues(results);
      setIssueStatus("success");
    } catch (err) {
      setIssueError(err instanceof ApiError ? err.message : "Fetching issues failed.");
      setIssueStatus("error");
    }
  }

  async function handleSelectIssue(issue: IssueResult) {
    if (!selectedRepo) return;
    setSandboxStatus("loading");
    setSandboxError(null);
    try {
      const cloneUrl = `https://github.com/${selectedRepo.full_name}.git`;
      const { workspace_id } = await createSandbox(cloneUrl);
      saveInvestigationContext({
        workspace_id,
        repo_full_name: selectedRepo.full_name,
        issue_title: issue.title,
        issue_body: `Issue #${issue.number}: ${issue.title}`,
      });
      setSandboxStatus("success");
      router.push("/investigate");
    } catch (err) {
      setSandboxError(
        err instanceof ApiError ? err.message : "Could not create a sandbox for this repo."
      );
      setSandboxStatus("error");
    }
  }

  return (
    <div className="space-y-8">
      {!profile && (
        <p role="alert" className="rounded border border-amber-800 bg-amber-950/40 px-3 py-2 text-sm text-amber-300">
          No developer profile found yet — issue scoring needs one. Set up your profile first.
        </p>
      )}

      <form onSubmit={handleSearch} className="flex gap-2 max-w-lg">
        <div className="flex-1">
          <label htmlFor="query" className="block text-sm font-medium text-slate-300 mb-1">
            Search query
          </label>
          <input
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="e.g. good first issue python"
          />
        </div>
        <button
          type="submit"
          disabled={repoStatus === "loading" || !query.trim()}
          className="self-end rounded bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 transition-colors disabled:opacity-50 h-9"
        >
          {repoStatus === "loading" ? "Searching…" : "Search"}
        </button>
      </form>

      {repoStatus === "error" && repoError && (
        <p role="alert" className="rounded border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300 max-w-lg">
          {repoError}
        </p>
      )}

      {repoStatus === "success" && repos.length === 0 && (
        <p className="text-sm text-slate-400">No repositories matched that search.</p>
      )}

      {repoStatus === "success" && repos.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {repos.map((repo) => (
            <button
              key={repo.full_name}
              type="button"
              onClick={() => handleSelectRepo(repo)}
              className={`text-left rounded border p-4 transition-colors ${
                selectedRepo?.full_name === repo.full_name
                  ? "border-indigo-500 bg-indigo-950/30"
                  : "border-slate-800 bg-slate-900 hover:border-slate-600"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="font-medium">{repo.full_name}</span>
                <span className="text-xs text-slate-500">★ {repo.stars}</span>
              </div>
              <ScoreBreakdown score={repo.score} breakdown={repo.breakdown} />
            </button>
          ))}
        </div>
      )}

      {selectedRepo && (
        <div>
          <h2 className="text-lg font-semibold mb-3">
            Issues in <span className="text-indigo-300">{selectedRepo.full_name}</span>
          </h2>

          {issueStatus === "loading" && (
            <p className="text-sm text-slate-400">Loading scored issues…</p>
          )}

          {issueStatus === "error" && issueError && (
            <p role="alert" className="rounded border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300 max-w-lg">
              {issueError}
            </p>
          )}

          {issueStatus === "success" && issues.length === 0 && (
            <p className="text-sm text-slate-400">No open issues found.</p>
          )}

          {issueStatus === "success" && issues.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2">
              {issues.map((issue) => (
                <button
                  key={issue.number}
                  type="button"
                  onClick={() => handleSelectIssue(issue)}
                  disabled={sandboxStatus === "loading"}
                  className="text-left rounded border border-slate-800 bg-slate-900 p-4 hover:border-slate-600 transition-colors disabled:opacity-50"
                >
                  <div className="mb-3">
                    <span className="text-xs text-slate-500">#{issue.number}</span>
                    <p className="font-medium">{issue.title}</p>
                  </div>
                  <ScoreBreakdown score={issue.score} breakdown={issue.breakdown} />
                </button>
              ))}
            </div>
          )}

          {sandboxStatus === "loading" && (
            <p className="mt-3 text-sm text-slate-400">Provisioning sandbox…</p>
          )}
          {sandboxStatus === "error" && sandboxError && (
            <p role="alert" className="mt-3 rounded border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300 max-w-lg">
              {sandboxError}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
