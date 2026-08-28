"use client";

import { useState } from "react";
import Link from "next/link";
import { ApiError, createProfile, type Proficiency } from "@/lib/api";
import { saveProfile, type StoredProfile } from "@/lib/storage";

const DOMAINS = [
  "backend",
  "frontend",
  "ai_agents",
  "devtools",
  "distributed_systems",
  "mobile",
  "data_engineering",
  "security",
] as const;

const LANGUAGE_LEVELS = ["beginner", "intermediate", "advanced"] as const;

interface LanguageEntry {
  name: string;
  level: string;
}

export function ProfileForm() {
  const [name, setName] = useState("");
  const [languages, setLanguages] = useState<LanguageEntry[]>([]);
  const [languageName, setLanguageName] = useState("");
  const [languageLevel, setLanguageLevel] = useState<string>(LANGUAGE_LEVELS[0]);
  const [domains, setDomains] = useState<string[]>([]);
  const [overallProficiency, setOverallProficiency] = useState<Proficiency>("intermediate");

  const [status, setStatus] = useState<"idle" | "loading" | "error" | "success">("idle");
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<StoredProfile | null>(null);

  function addLanguage() {
    const trimmed = languageName.trim();
    if (!trimmed) return;
    setLanguages((prev) => [...prev, { name: trimmed, level: languageLevel }]);
    setLanguageName("");
  }

  function removeLanguage(name: string) {
    setLanguages((prev) => prev.filter((l) => l.name !== name));
  }

  function toggleDomain(domain: string) {
    setDomains((prev) =>
      prev.includes(domain) ? prev.filter((d) => d !== domain) : [...prev, domain]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setError(null);

    const languageMap = Object.fromEntries(languages.map((l) => [l.name, l.level]));

    try {
      const profile = await createProfile({ name, languages: languageMap, domains });
      const stored: StoredProfile = { ...profile, proficiency: overallProficiency };
      saveProfile(stored);
      setCreated(stored);
      setStatus("success");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setStatus("error");
    }
  }

  if (status === "success" && created) {
    return (
      <div
        data-testid="profile-success"
        className="rounded border border-emerald-800 bg-emerald-950/40 p-6"
      >
        <h2 className="text-lg font-semibold text-emerald-300 mb-1">Profile created</h2>
        <p className="text-slate-300">
          Welcome, <strong>{created.name}</strong>. Your profile id{" "}
          <code className="text-emerald-400">{created.id}</code> is saved locally.
        </p>
        <Link
          href="/discover"
          className="mt-4 inline-block rounded bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 transition-colors"
        >
          Discover issues →
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-xl space-y-6">
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-slate-300 mb-1">
          Your name
        </label>
        <input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
        />
      </div>

      <div>
        <span className="block text-sm font-medium text-slate-300 mb-1">
          Overall proficiency
        </span>
        <select
          aria-label="overall proficiency"
          value={overallProficiency}
          onChange={(e) => setOverallProficiency(e.target.value as Proficiency)}
          className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
        >
          {LANGUAGE_LEVELS.map((lvl) => (
            <option key={lvl} value={lvl}>
              {lvl}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-slate-500">
          Used to calibrate hint style in the Mentor Workspace.
        </p>
      </div>

      <fieldset>
        <legend className="block text-sm font-medium text-slate-300 mb-1">Languages</legend>
        <div className="flex gap-2 items-end mb-2">
          <div>
            <label htmlFor="language-name" className="block text-xs text-slate-500 mb-1">
              Language name
            </label>
            <input
              id="language-name"
              value={languageName}
              onChange={(e) => setLanguageName(e.target.value)}
              className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="language-level" className="block text-xs text-slate-500 mb-1">
              Proficiency level
            </label>
            <select
              id="language-level"
              value={languageLevel}
              onChange={(e) => setLanguageLevel(e.target.value)}
              className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            >
              {LANGUAGE_LEVELS.map((lvl) => (
                <option key={lvl} value={lvl}>
                  {lvl}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={addLanguage}
            className="rounded border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800"
          >
            Add language
          </button>
        </div>
        {languages.length > 0 && (
          <ul className="space-y-1">
            {languages.map((l) => (
              <li
                key={l.name}
                className="flex items-center justify-between rounded bg-slate-900 px-3 py-1 text-sm"
              >
                <span>
                  {l.name} — {l.level}
                </span>
                <button
                  type="button"
                  onClick={() => removeLanguage(l.name)}
                  className="text-slate-500 hover:text-red-400"
                  aria-label={`remove ${l.name}`}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </fieldset>

      <fieldset>
        <legend className="block text-sm font-medium text-slate-300 mb-2">Domains</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {DOMAINS.map((domain) => (
            <label key={domain} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={domains.includes(domain)}
                onChange={() => toggleDomain(domain)}
              />
              {domain.replace(/_/g, " ")}
            </label>
          ))}
        </div>
      </fieldset>

      {status === "error" && error && (
        <p role="alert" className="rounded border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={status === "loading" || !name.trim()}
        className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 transition-colors disabled:opacity-50"
      >
        {status === "loading" ? "Creating…" : "Create profile"}
      </button>
    </form>
  );
}
