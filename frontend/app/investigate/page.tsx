import { InvestigateView } from "@/components/investigate/InvestigateView";

export default function InvestigatePage() {
  return (
    <div>
      <h1 className="text-xl font-semibold mb-1">Investigation</h1>
      <p className="text-slate-400 mb-6 text-sm">
        Watch the agent reason through the codebase, one hypothesis at a time.
      </p>
      <InvestigateView />
    </div>
  );
}
