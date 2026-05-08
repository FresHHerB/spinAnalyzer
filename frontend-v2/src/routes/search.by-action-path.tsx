import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ResultsList } from "@/components/search/ResultsList";

const STREETS = ["preflop", "flop", "turn", "river"];

export const Route = createFileRoute("/search/by-action-path")({
  component: SearchByActionPathPage,
});

function SearchByActionPathPage() {
  const villains = useQuery({
    queryKey: ["villains"],
    queryFn: api.listVillains,
  });

  const [villain, setVillain] = useState("");
  const [street, setStreet] = useState("flop");
  const [path, setPath] = useState("V_X-H_X");
  const [k, setK] = useState(50);

  const mutation = useMutation({
    mutationFn: () =>
      api.searchByActionPath({
        villain_name: villain,
        street,
        action_path: path,
        k,
      }),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold">Search by action path</h2>
      <p className="text-muted-foreground">
        Filter decision points by exact action sequence on a single street.
        Tokens: <code className="font-mono">H</code>/<code className="font-mono">V</code>{" "}
        + <code className="font-mono">X</code> (check), <code className="font-mono">C</code>{" "}
        (call), <code className="font-mono">F</code> (fold), <code className="font-mono">B</code>{" "}
        (bet %pot), <code className="font-mono">R</code> (raise).
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Query</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
          >
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <label className="text-xs text-muted-foreground">Villain</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={villain}
                  onChange={(e) => setVillain(e.target.value)}
                >
                  <option value="">— select —</option>
                  {villains.data?.villains.map((v) => (
                    <option key={v.name} value={v.name}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Street</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={street}
                  onChange={(e) => setStreet(e.target.value)}
                >
                  {STREETS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">k</label>
                <Input
                  type="number"
                  min={1}
                  max={500}
                  value={k}
                  onChange={(e) => setK(Number(e.target.value))}
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Action path</label>
              <Input
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="V_X-H_B50-V_C"
                className="font-mono"
              />
            </div>
            <Button type="submit" disabled={!villain || mutation.isPending}>
              {mutation.isPending ? "Searching…" : "Search"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {mutation.data && (
        <ResultsList
          results={mutation.data.results}
          searchTimeMs={mutation.data.search_time_ms}
        />
      )}
    </div>
  );
}
