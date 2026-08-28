import { DiscoverView } from "@/components/discover/DiscoverView";

export default function DiscoverPage() {
  return (
    <div>
      <h1 className="text-xl font-semibold mb-1">Discover an issue</h1>
      <p className="text-slate-400 mb-6 text-sm">
        Every score shown below is a deterministic breakdown, not a black box —
        see exactly why a repo or issue ranked the way it did.
      </p>
      <DiscoverView />
    </div>
  );
}
