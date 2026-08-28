interface ScoreBreakdownProps {
  score: number;
  breakdown: Record<string, number>;
}

export function ScoreBreakdown({ score, breakdown }: ScoreBreakdownProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs uppercase tracking-wide text-slate-500">Score</span>
        <span className="text-lg font-semibold text-indigo-300">{score.toFixed(3)}</span>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {Object.entries(breakdown).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between gap-2">
            <dt className="text-slate-500 truncate" title={key}>
              {key.replace(/_/g, " ")}
            </dt>
            <dd className="text-slate-300 font-mono">{value.toFixed(3)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
