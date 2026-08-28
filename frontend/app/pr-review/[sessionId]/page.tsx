import { PrReviewView } from "@/components/pr-review/PrReviewView";

export default function PrReviewPage({ params }: { params: { sessionId: string } }) {
  return (
    <div>
      <h1 className="text-xl font-semibold mb-1">PR Review</h1>
      <p className="text-slate-400 mb-6 text-sm">
        Review the diff, then approve and push or ask for changes.
      </p>
      <PrReviewView sessionId={params.sessionId} />
    </div>
  );
}
