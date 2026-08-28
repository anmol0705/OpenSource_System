import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold mb-2">Enterprise Support Agent</h1>
      <p className="text-slate-400 mb-6">
        Set up your developer profile, discover a scored issue, watch the
        investigation reason through the codebase, get mentored through a
        real fix, then ship the PR.
      </p>
      <Link
        href="/profile"
        className="inline-block rounded bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 transition-colors"
      >
        Start with your profile →
      </Link>
    </div>
  );
}
