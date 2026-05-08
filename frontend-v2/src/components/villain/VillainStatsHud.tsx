import type { VillainProfile } from "@/lib/api-types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { pct } from "@/lib/utils";

const STATS: { key: keyof VillainProfile; label: string }[] = [
  { key: "vpip", label: "VPIP" },
  { key: "pfr", label: "PFR" },
  { key: "threebet_pct", label: "3-bet" },
  { key: "cbet_flop_pct", label: "C-bet flop" },
  { key: "fold_to_cbet_pct", label: "Fold to C-bet" },
  { key: "donk_freq", label: "Donk freq" },
  { key: "xr_freq", label: "Check-raise" },
  { key: "sb_limp_pct", label: "SB limp" },
  { key: "showdown_pct", label: "Showdown" },
];

export function VillainStatsHud({ profile }: { profile: VillainProfile }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Stats</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-3 gap-4">
        {STATS.map(({ key, label }) => (
          <div key={key as string}>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-lg font-semibold">{pct(profile[key] as number | null)}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
