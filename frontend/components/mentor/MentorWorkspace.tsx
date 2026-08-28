"use client";

import { useState } from "react";
import Link from "next/link";
import Editor from "@monaco-editor/react";
import { ApiError, submitMentorAttempt } from "@/lib/api";
import { loadMentorContext, savePrContext } from "@/lib/storage";

const MAX_HINTS = 4;

interface HintEntry {
  text: string;
  order: number;
}

type SubmitStatus = "idle" | "loading" | "error";

interface MentorWorkspaceProps {
  sessionId: string;
}

export function MentorWorkspace({ sessionId }: MentorWorkspaceProps) {
  const [context] = useState(() => loadMentorContext(sessionId));

  const [code, setCode] = useState(context?.original_content ?? "");
  const [hints, setHints] = useState<HintEntry[]>(() =>
    context?.initial_hint
      ? [{ text: context.initial_hint, order: context.initial_hint_count }]
      : []
  );
  const [hintCount, setHintCount] = useState(context?.initial_hint_count ?? 0);
  const [hasUnreadHint, setHasUnreadHint] = useState(hints.length > 0);

  const [status, setStatus] = useState<SubmitStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [testOutput, setTestOutput] = useState<string | null>(null);
  const [testsPassed, setTestsPassed] = useState(false);

  if (!context) {
    return (
      <p className="text-sm text-slate-400">
        No mentoring session found. Go back to{" "}
        <a href="/investigate" className="text-indigo-400 underline">
          Investigation
        </a>{" "}
        and start one.
      </p>
    );
  }

  async function handleRunTests() {
    setStatus("loading");
    setError(null);
    try {
      const res = await submitMentorAttempt(sessionId, { human_attempt: code });
      setTestOutput(res.test_output);
      setTestsPassed(res.tests_passed);
      setStatus("idle");

      if (res.tests_passed) {
        savePrContext(sessionId, {
          workspace_id: context!.workspace_id,
          repo_full_name: context!.repo_full_name,
          target_file: context!.target_file,
          original_content: context!.original_content,
          final_content: code,
          test_command: context!.test_command,
          issue_title: context!.issue_title,
          issue_body: context!.issue_body,
        });
      } else if (res.hint) {
        setHints((prev) => [...prev, { text: res.hint!, order: res.hint_count }]);
        setHintCount(res.hint_count);
        setHasUnreadHint(true);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit your attempt.");
      setStatus("error");
    }
  }

  function acknowledgeHint() {
    setHasUnreadHint(false);
  }

  const runDisabled = status === "loading" || hasUnreadHint || testsPassed;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-4">
        <div className="rounded border border-slate-800 bg-slate-900 p-4">
          <h2 className="text-lg font-semibold">{context.issue_title}</h2>
          <p className="mt-1 text-sm text-slate-400 whitespace-pre-wrap">{context.issue_body}</p>
          <p className="mt-2 text-xs font-mono text-slate-500">{context.target_file}</p>
        </div>

        <div className="rounded border border-slate-800 bg-slate-900 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-300">Hints</h3>
            {hints.length > 0 && (
              <span className="text-xs text-slate-500">
                Hint {hintCount} of {MAX_HINTS}
              </span>
            )}
          </div>

          {hints.length === 0 && (
            <p className="text-sm text-slate-500">No hints yet — run tests to get one.</p>
          )}

          <ul className="space-y-2">
            {hints.map((hint, i) => {
              const isLatest = i === hints.length - 1;
              return (
                <li
                  key={i}
                  className={`rounded border p-3 text-sm ${
                    isLatest && hasUnreadHint
                      ? "border-amber-600 bg-amber-950/30 animate-[fadeIn_0.3s_ease-in]"
                      : "border-slate-800 bg-slate-950/40 text-slate-400"
                  }`}
                >
                  {hint.text}
                </li>
              );
            })}
          </ul>

          {hasUnreadHint && (
            <button
              type="button"
              onClick={acknowledgeHint}
              className="mt-3 rounded border border-amber-700 px-3 py-1.5 text-sm text-amber-300 hover:bg-amber-950/40"
            >
              I&apos;ve read this hint
            </button>
          )}
        </div>

        {testOutput !== null && (
          <div className="rounded border border-slate-800 bg-black p-3">
            <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">Test output</p>
            <pre className="whitespace-pre-wrap text-xs font-mono text-emerald-300">
              {testOutput}
            </pre>
          </div>
        )}

        {testsPassed && (
          <div className="rounded border border-emerald-800 bg-emerald-950/40 p-4">
            <p className="font-semibold text-emerald-300">Tests passed</p>
            <p className="text-sm text-slate-300 mt-1">
              Your fix works. Ready to send it out for review.
            </p>
            <Link
              href={`/pr-review/${sessionId}`}
              className="mt-3 inline-block rounded bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 transition-colors"
            >
              Proceed to PR Review →
            </Link>
          </div>
        )}

        {status === "error" && error && (
          <p role="alert" className="rounded border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={handleRunTests}
          disabled={runDisabled}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 transition-colors disabled:opacity-50"
        >
          {status === "loading" ? "Running tests…" : "Run Tests"}
        </button>
        {hasUnreadHint && (
          <p className="text-xs text-amber-500">
            Read the new hint above before running tests again.
          </p>
        )}
      </div>

      <div className="rounded border border-slate-800 overflow-hidden h-[560px]">
        <Editor
          height="100%"
          theme="vs-dark"
          language={guessLanguage(context.target_file)}
          value={code}
          onChange={(value) => setCode(value ?? "")}
          options={{ minimap: { enabled: false }, fontSize: 13 }}
        />
      </div>
    </div>
  );
}

function guessLanguage(path: string): string {
  if (path.endsWith(".py")) return "python";
  if (path.endsWith(".ts") || path.endsWith(".tsx")) return "typescript";
  if (path.endsWith(".js") || path.endsWith(".jsx")) return "javascript";
  if (path.endsWith(".go")) return "go";
  if (path.endsWith(".rs")) return "rust";
  return "plaintext";
}
