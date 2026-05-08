import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { VillainStatsHud } from "@/components/villain/VillainStatsHud";
import { SizingHistogramChart } from "@/components/charts/SizingHistogramChart";
import { pct } from "@/lib/utils";

export const Route = createFileRoute("/villains/$name")({
  component: VillainProfilePage,
});

function VillainProfilePage() {
  const { name } = Route.useParams();
  const profile = useQuery({
    queryKey: ["villain", name],
    queryFn: () => api.getVillain(name),
  });
  const sizing = useQuery({
    queryKey: ["villain-sizing", name],
    queryFn: () => api.getVillainSizing(name),
  });

  if (profile.error)
    return (
      <p className="text-destructive">
        Villain {name} not found.
      </p>
    );
  if (!profile.data) return <p className="text-muted-foreground">Loading…</p>;

  const p = profile.data;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold">{p.name}</h2>
          <p className="text-muted-foreground">
            {p.n_hands} hands • {p.n_decisions} decision points
          </p>
        </div>
        {p.archetype && <Badge className="text-base">{p.archetype}</Badge>}
      </header>

      <VillainStatsHud profile={p} />

      <Card>
        <CardHeader>
          <CardTitle>Avg bet sizing per street (% pot)</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-6">
          <Stat label="Flop" value={pct(p.avg_bet_pot_pct_flop)} />
          <Stat label="Turn" value={pct(p.avg_bet_pot_pct_turn)} />
          <Stat label="River" value={pct(p.avg_bet_pot_pct_river)} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Bet-size distribution</CardTitle>
        </CardHeader>
        <CardContent>
          {sizing.data ? (
            sizing.data.buckets.length > 0 ? (
              <SizingHistogramChart buckets={sizing.data.buckets} />
            ) : (
              <p className="text-muted-foreground">
                No postflop bets observed for this villain.
              </p>
            )
          ) : (
            <p className="text-muted-foreground">Loading…</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase text-muted-foreground">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}
