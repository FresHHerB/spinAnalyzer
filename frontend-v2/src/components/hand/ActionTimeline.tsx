import type { DecisionResponse } from "@/lib/api-types";
import { cn } from "@/lib/utils";

const STREET_ORDER = ["preflop", "flop", "turn", "river"];

export function ActionTimeline({
  decisions,
  selected,
  onSelect,
}: {
  decisions: DecisionResponse[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const byStreet = STREET_ORDER.map((street) => ({
    street,
    items: decisions.filter((d) => d.street === street),
  })).filter((s) => s.items.length > 0);

  return (
    <div className="flex flex-col gap-4">
      {byStreet.map((s) => (
        <div key={s.street}>
          <p className="mb-2 text-xs uppercase text-muted-foreground">
            {s.street}
          </p>
          <div className="flex flex-wrap gap-2">
            {s.items.map((dp) => (
              <button
                key={dp.decision_id}
                onClick={() => onSelect(dp.decision_id)}
                className={cn(
                  "rounded-md border px-3 py-2 text-sm transition-colors",
                  selected === dp.decision_id
                    ? "border-primary bg-secondary"
                    : "border-border hover:bg-secondary/50",
                )}
              >
                {dp.villain_position} {dp.villain_action}
                {dp.villain_bet_size_pot_pct !== null &&
                  dp.villain_bet_size_pot_pct !== undefined && (
                    <span className="ml-1 text-muted-foreground">
                      {Math.round(dp.villain_bet_size_pot_pct)}%
                    </span>
                  )}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
