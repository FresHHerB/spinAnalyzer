import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { pct } from "@/lib/utils";

export const Route = createFileRoute("/")({
  component: DashboardPage,
});

function DashboardPage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
  });
  const villains = useQuery({
    queryKey: ["villains"],
    queryFn: api.listVillains,
  });

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Overview of the indexed villain dataset.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Kpi
          title="Indexed villains"
          value={health.data?.n_villains ?? "—"}
          loading={health.isLoading}
        />
        <Kpi
          title="Decision points"
          value={health.data?.n_decisions?.toLocaleString() ?? "—"}
          loading={health.isLoading}
        />
        <Kpi
          title="API status"
          value={health.data?.status ?? "—"}
          loading={health.isLoading}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Villains</CardTitle>
        </CardHeader>
        <CardContent>
          {villains.isLoading ? (
            <p className="text-muted-foreground">Loading…</p>
          ) : villains.error ? (
            <p className="text-destructive">Failed to load villains.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Archetype</TableHead>
                  <TableHead className="text-right">Hands</TableHead>
                  <TableHead className="text-right">DPs</TableHead>
                  <TableHead className="text-right">VPIP</TableHead>
                  <TableHead className="text-right">PFR</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {villains.data?.villains.map((v) => (
                  <TableRow key={v.name}>
                    <TableCell className="font-medium">
                      <Link
                        to="/villains/$name"
                        params={{ name: v.name }}
                        className="hover:underline"
                      >
                        {v.name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      {v.archetype && (
                        <Badge variant={archetypeVariant(v.archetype)}>
                          {v.archetype}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">{v.n_hands}</TableCell>
                    <TableCell className="text-right">{v.n_decisions}</TableCell>
                    <TableCell className="text-right">{pct(v.vpip)}</TableCell>
                    <TableCell className="text-right">{pct(v.pfr)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Kpi({
  title,
  value,
  loading,
}: {
  title: string;
  value: string | number;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{loading ? "…" : value}</p>
      </CardContent>
    </Card>
  );
}

function archetypeVariant(
  archetype: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (archetype) {
    case "Maniac":
    case "Fish":
      return "destructive";
    case "Nit":
      return "outline";
    case "TAG":
    case "LAG":
      return "default";
    default:
      return "secondary";
  }
}
