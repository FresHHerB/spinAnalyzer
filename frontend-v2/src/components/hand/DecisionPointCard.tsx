import type { DecisionResponse } from "@/lib/api-types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BoardDisplay } from "./BoardDisplay";
import { pct, fmt } from "@/lib/utils";

export function DecisionPointCard({ dp }: { dp: DecisionResponse }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            {dp.street.toUpperCase()} • {dp.villain_position} • {dp.villain_action.toUpperCase()}
          </CardTitle>
          <div className="flex gap-2">
            {dp.intent && <Badge variant="secondary">{dp.intent}</Badge>}
            {dp.line_tag && dp.line_tag !== "none" && (
              <Badge variant="outline">{dp.line_tag}</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {dp.board_cards.length > 0 && (
          <BoardDisplay cards={dp.board_cards} size="sm" />
        )}
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <Field label="Pot (BB)" value={fmt(dp.pot_bb)} />
          <Field label="Eff stack (BB)" value={fmt(dp.eff_stack_bb)} />
          <Field label="SPR" value={fmt(dp.spr, 2)} />
          <Field label="Bet %pot" value={pct(dp.villain_bet_size_pot_pct)} />
        </div>
        {dp.villain_hand && (
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">
              Villain showed {dp.villain_made_specific && (
                <Badge variant="secondary">{dp.villain_made_specific}</Badge>
              )}
            </p>
            <div className="mt-2">
              <BoardDisplay cards={dp.villain_hand} size="sm" />
            </div>
            {dp.villain_equity_vs_random !== null &&
              dp.villain_equity_vs_random !== undefined && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Equity vs random: {pct(dp.villain_equity_vs_random * 100)}
                </p>
              )}
          </div>
        )}
        {dp.action_path && (
          <p className="font-mono text-xs text-muted-foreground">
            path: {dp.action_path}
          </p>
        )}
        {dp.distance !== null && dp.distance !== undefined && (
          <p className="text-xs text-muted-foreground">
            distance: {fmt(dp.distance, 4)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}
