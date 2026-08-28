import { MentorWorkspace } from "@/components/mentor/MentorWorkspace";

export default function MentorPage({ params }: { params: { sessionId: string } }) {
  return (
    <div>
      <h1 className="text-xl font-semibold mb-1">Mentor Workspace</h1>
      <p className="text-slate-400 mb-6 text-sm">
        Write the fix yourself. Hints are Socratic nudges, never the answer.
      </p>
      <MentorWorkspace sessionId={params.sessionId} />
    </div>
  );
}
