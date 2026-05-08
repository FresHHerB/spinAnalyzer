import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ActionTimeline } from "@/components/hand/ActionTimeline";
import { DecisionPointCard } from "@/components/hand/DecisionPointCard";
import { BoardDisplay } from "@/components/hand/BoardDisplay";

export const Route = createFileRoute("/hands/$id")({
  component: HandDetailPage,
});

function HandDetailPage() {
  const { id } = Route.useParams();
  const { data, isLoading, error } = useQuery({
    queryKey: ["hand", id],
    queryFn: () => api.getHand(id),
  });

  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = useMemo(
    () => data?.decisions.find((d) => d.decision_id === selectedId) ?? data?.decisions[0],
    [data, selectedId],
  );

  if (isLoading) return <p className="text-muted-foreground">Loading…</p>;
  if (error || !data)
    return <p className="text-destructive">Hand {id} not found.</p>;

  const finalBoard =
    data.decisions.find((d) => d.street === "river")?.board_cards ??
    data.decisions.find((d) => d.street === "turn")?.board_cards ??
    data.decisions.find((d) => d.street === "flop")?.board_cards ??
    [];

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-3xl font-bold">Hand {data.hand_id}</h2>
        <p className="text-muted-foreground">
          Villain:{" "}
          <Link
            to="/villains/$name"
            params={{ name: data.villain_name }}
            className="hover:underline"
          >
            {data.villain_name}
          </Link>
          {" • "}
          {data.decisions.length} decision points
        </p>
      </header>

      {finalBoard.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Final board</CardTitle>
          </CardHeader>
          <CardContent>
            <BoardDisplay cards={finalBoard} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Action timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <ActionTimeline
            decisions={data.decisions}
            selected={selectedId ?? data.decisions[0]?.decision_id ?? null}
            onSelect={setSelectedId}
          />
        </CardContent>
      </Card>

      {selected && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Selected decision</h3>
            <Link to="/search/by-decision" search={{ decision_id: selected.decision_id }}>
              <Button variant="outline" size="sm">
                Find similar
              </Button>
            </Link>
          </div>
          <DecisionPointCard dp={selected} />
        </div>
      )}
    </div>
  );
}
