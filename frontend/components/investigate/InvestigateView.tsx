"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  investigate,
  runSandboxCommand,
  startMentorSession,
  type InvestigateResponse,
} from "@/lib/api";
import {
  loadInvestigationContext,
  loadProfile,
  saveMentorContext,
} from "@/lib/storage";

type Status = "idle" | "loading" | "error" | "success";

function parseIteration(line: string): { label: string; text: string } {
  const match = line.match(/^(iteration \d+):\s*(.*)$/i);
  if (match) return { label: match[1], text: match[2] };
  return { label: "step", text: line };
}

export function InvestigateView() {
  const router = useRouter();
  const [context] = useState(() => loadInvestigationContext());

  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InvestigateResponse | null>(null);

  const [mentorStatus, setMentorStatus] = useState<Status>("idle");
  const [mentorError, setMentorError] = useState<string | null>(null);

  useEffect(() => {
    if (!context) return;
    let cancelled = false;

    async function run() {
      setStatus("loading");
      setError(null);
      try {
        const res = await investigate(context!.workspace_id, {
          issue_title: context!.issue_title,
          issue_body: context!.issue_body,
        });
        if (!cancelled) {
          setResult(res);
          setStatus("success");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Investigation failed.");
          setStatus("error");
        }
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [context]);

  async function handleStartMentoring() {
    if (!context || !result) return;
    setMentorStatus("loading");
    setMentorError(null);

    const profile = loadProfile();
    if (!profile) {
      setMentorError("No developer profile found. Set up your profile first.");
      setMentorStatus("error");
      return;
    }

    try {
      const { output } = await runSandboxCommand(
        context.workspace_id,
        `cat "${result.target_file}"`
      );

      const testCommand = "python -m pytest";
      const mentorRes = await startMentorSession(context.workspace_id, {
        issue_title: context.issue_title,
        issue_body: context.issue_body,
        target_file: result.target_file,
        original_content: output,
        test_command: testCommand,
        proficiency: profile.proficiency,
      });

      saveMentorContext(mentorRes.session_id, {
        workspace_id: context.workspace_id,
        repo_full_name: context.repo_full_name,
        target_file: result.target_file,
        original_content: output,
        test_command: testCommand,
        issue_title: context.issue_title,
        issue_body: context.issue_body,
        initial_hint: mentorRes.hint,
        initial_hint_count: mentorRes.hint_count,
      });

      setMentorStatus("success");
      router.push(`/mentor/${mentorRes.session_id}`);
    } catch (err) {
      setMentorError(
        err instanceof ApiError ? err.message : "Could not start a mentoring session."
      );
      setMentorStatus("error");
    }
  }

  if (!context) {
    return (
      <p className="text-sm text-slate-400">
        No investigation in progress. Go to{" "}
        <a href="/discover" className="text-indigo-400 underline">
          Discover
        </a>{" "}
        and select an issue first.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">{context.issue_title}</h2>
        <p className="text-sm text-slate-500">{context.repo_full_name}</p>
      </div>

      {status === "loading" && (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-400" />
          Investigating the codebase…
        </div>
      )}

      {status === "error" && error && (
        <p role="alert" className="rounded border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      {status === "success" && result && (
        <>
          <ol className="space-y-3 border-l border-slate-800 pl-4">
            {result.history.map((line, i) => {
              const { label, text } = parseIteration(line);
              return (
                <li key={i} className="relative">
                  <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-indigo-500" />
                  <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                  <p className="text-sm text-slate-200">{text}</p>
                </li>
              );
            })}
          </ol>

          <div className="rounded border border-indigo-800 bg-indigo-950/30 p-4 space-y-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Target file</p>
              <p className="font-mono text-indigo-300">{result.target_file}</p>
            </div>

            <div>
              <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                <span>Final confidence</span>
                <span>{Math.round(result.confidence * 100)}%</span>
              </div>
              <div className="h-2 w-full rounded bg-slate-800">
                <div
                  className="h-2 rounded bg-indigo-500"
                  style={{ width: `${Math.round(result.confidence * 100)}%` }}
                />
              </div>
            </div>

            <p className="text-xs text-slate-500">
              {result.iterations} iteration{result.iterations === 1 ? "" : "s"} · files
              inspected: {result.files_inspected.join(", ") || "none"}
              {result.files_with_history_checked.length > 0 && (
                <> · git history checked for: {result.files_with_history_checked.join(", ")}</>
              )}
            </p>

            <button
              type="button"
              onClick={handleStartMentoring}
              disabled={mentorStatus === "loading"}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 transition-colors disabled:opacity-50"
            >
              {mentorStatus === "loading" ? "Starting…" : "Start Mentoring Session"}
            </button>

            {mentorStatus === "error" && mentorError && (
              <p role="alert" className="rounded border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300">
                {mentorError}
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
