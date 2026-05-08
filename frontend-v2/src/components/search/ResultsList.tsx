import type { DecisionResponse } from "@/lib/api-types";
import { DecisionPointCard } from "@/components/hand/DecisionPointCard";

export function ResultsList({
  results,
  searchTimeMs,
}: {
  results: DecisionResponse[];
  searchTimeMs?: number;
}) {
  if (results.length === 0) {
    return (
      <p className="text-muted-foreground">No matching decision points.</p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {results.length} results
        {searchTimeMs !== undefined && ` • ${searchTimeMs.toFixed(1)}ms`}
      </p>
      {results.map((dp) => (
        <DecisionPointCard key={dp.decision_id} dp={dp} />
      ))}
    </div>
  );
}
