import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { pct } from "@/lib/utils";

export const Route = createFileRoute("/villains/")({
  component: VillainListPage,
});

function VillainListPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["villains"],
    queryFn: api.listVillains,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold">Villains</h2>
      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data?.villains.map((v) => (
          <Link
            key={v.name}
            to="/villains/$name"
            params={{ name: v.name }}
          >
            <Card className="transition-colors hover:border-primary">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{v.name}</CardTitle>
                  {v.archetype && <Badge>{v.archetype}</Badge>}
                </div>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p>
                  <span className="text-muted-foreground">Hands:</span>{" "}
                  <strong>{v.n_hands}</strong>
                </p>
                <p>
                  <span className="text-muted-foreground">DPs:</span>{" "}
                  <strong>{v.n_decisions}</strong>
                </p>
                <p>
                  <span className="text-muted-foreground">VPIP / PFR:</span>{" "}
                  <strong>{pct(v.vpip)} / {pct(v.pfr)}</strong>
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
