"use client";

import { useState } from "react";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";
import { ApiError, approvePr, requestPrApproval } from "@/lib/api";
import { loadPrContext } from "@/lib/storage";

type Status = "idle" | "loading" | "error" | "success";

interface PrReviewViewProps {
  sessionId: string;
}

export function PrReviewView({ sessionId }: PrReviewViewProps) {
  const [context] = useState(() => loadPrContext(sessionId));

  const [branchName, setBranchName] = useState(
    () => `apprentice/fix-${sessionId.slice(0, 8)}`
  );
  const [commitMessage, setCommitMessage] = useState(
    () => context?.issue_title ?? "Fix issue"
  );
  const [prTitle, setPrTitle] = useState(() => context?.issue_title ?? "Fix issue");
  const [prBody, setPrBody] = useState(() => context?.issue_body ?? "");
  const [feedback, setFeedback] = useState("");
  const [savedFeedback, setSavedFeedback] = useState<string | null>(null);

  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [prUrl, setPrUrl] = useState<string | null>(null);

  if (!context) {
    return (
      <p className="text-sm text-slate-400">
        No passing mentor session found for this review. Finish a fix in the{" "}
        <a href="/discover" className="text-indigo-400 underline">
          Mentor Workspace
        </a>{" "}
        first.
      </p>
    );
  }

  async function handleApproveAndPush() {
    setStatus("loading");
    setError(null);
    setSavedFeedback(null);
    try {
      const approval = await requestPrApproval(context!.workspace_id, {
        repo_full_name: context!.repo_full_name,
        branch_name: branchName,
        target_file: context!.target_file,
        final_content: context!.final_content,
        commit_message: commitMessage,
        pr_title: prTitle,
        pr_body: prBody,
        test_command: context!.test_command,
        issue_title: context!.issue_title,
        issue_body: context!.issue_body,
      });

      const approved = await approvePr(approval.session_id);
      if (approved.status === "pushed" && approved.pr_number != null) {
        setPrUrl(`https://github.com/${context!.repo_full_name}/pull/${approved.pr_number}`);
        setStatus("success");
      } else {
        setError(`PR was not pushed (status: ${approved.status}).`);
        setStatus("error");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not push the PR.");
      setStatus("error");
    }
  }

  async function handleRequestChanges() {
    if (!feedback.trim()) return;
    setStatus("loading");
    setError(null);
    try {
      await requestPrApproval(context!.workspace_id, {
        repo_full_name: context!.repo_full_name,
        branch_name: branchName,
        target_file: context!.target_file,
        final_content: context!.final_content,
        commit_message: commitMessage,
        pr_title: prTitle,
        pr_body: prBody,
        test_command: context!.test_command,
        issue_title: context!.issue_title,
        issue_body: context!.issue_body,
      });
      setSavedFeedback(feedback);
      setStatus("idle");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the change request.");
      setStatus("error");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">{context.issue_title}</h2>
        <p className="text-sm text-slate-500 font-mono">{context.target_file}</p>
      </div>

      {context.teaching_summary && (
        <div className="rounded border border-slate-800 bg-slate-900 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Teaching summary</p>
          <p className="text-sm text-slate-300 whitespace-pre-wrap">{context.teaching_summary}</p>
        </div>
      )}

      <div className="rounded border border-slate-800 overflow-hidden text-sm">
        <ReactDiffViewer
          oldValue={context.original_content}
          newValue={context.final_content}
          splitView={false}
          useDarkTheme
          compareMethod={DiffMethod.WORDS}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 max-w-3xl">
        <div>
          <label htmlFor="branch-name" className="block text-sm font-medium text-slate-300 mb-1">
            Branch name
          </label>
          <input
            id="branch-name"
            value={branchName}
            onChange={(e) => setBranchName(e.target.value)}
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label htmlFor="commit-message" className="block text-sm font-medium text-slate-300 mb-1">
            Commit message
          </label>
          <input
            id="commit-message"
            value={commitMessage}
            onChange={(e) => setCommitMessage(e.target.value)}
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label htmlFor="pr-title" className="block text-sm font-medium text-slate-300 mb-1">
            PR title
          </label>
          <input
            id="pr-title"
            value={prTitle}
            onChange={(e) => setPrTitle(e.target.value)}
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="pr-body" className="block text-sm font-medium text-slate-300 mb-1">
            PR body
          </label>
          <textarea
            id="pr-body"
            value={prBody}
            onChange={(e) => setPrBody(e.target.value)}
            rows={3}
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          />
        </div>
      </div>

      {status === "error" && error && (
        <p role="alert" className="rounded border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300 max-w-3xl">
          {error}
        </p>
      )}

      {status === "success" && prUrl && (
        <div className="rounded border border-emerald-800 bg-emerald-950/40 p-4 max-w-3xl">
          <p className="font-semibold text-emerald-300">Pushed</p>
          <a
            href={prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-block text-indigo-400 underline break-all"
          >
            View pull request →
          </a>
        </div>
      )}

      <div className="flex flex-wrap gap-6 items-start max-w-3xl">
        <button
          type="button"
          onClick={handleApproveAndPush}
          disabled={status === "loading"}
          className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 transition-colors disabled:opacity-50"
        >
          {status === "loading" ? "Pushing…" : "Approve & Push"}
        </button>

        <div className="flex-1 min-w-[240px]">
          <label htmlFor="feedback" className="block text-sm font-medium text-slate-300 mb-1">
            Change request feedback
          </label>
          <textarea
            id="feedback"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={2}
            placeholder="What needs to change before this can be approved?"
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={handleRequestChanges}
            disabled={status === "loading" || !feedback.trim()}
            className="mt-2 rounded border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800 disabled:opacity-50"
          >
            Request changes
          </button>
          {savedFeedback && (
            <p data-testid="saved-feedback" className="mt-2 text-xs text-amber-400">
              Feedback recorded locally (no backend endpoint persists review
              comments yet): &ldquo;{savedFeedback}&rdquo;
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
