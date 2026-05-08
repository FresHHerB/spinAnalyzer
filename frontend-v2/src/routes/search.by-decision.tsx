import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ResultsList } from "@/components/search/ResultsList";
import { z } from "zod";

const searchSchema = z.object({
  decision_id: z.string().optional(),
});

export const Route = createFileRoute("/search/by-decision")({
  component: SearchByDecisionPage,
  validateSearch: searchSchema.parse,
});

function SearchByDecisionPage() {
  const params = Route.useSearch();
  const [decisionId, setDecisionId] = useState(params.decision_id ?? "");
  const [k, setK] = useState(20);

  const mutation = useMutation({
    mutationFn: () =>
      api.searchByDecision({ decision_id: decisionId, k }),
  });

  // Auto-search if decision_id was passed in via URL
  useEffect(() => {
    if (params.decision_id) {
      mutation.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold">Search by decision</h2>
      <p className="text-muted-foreground">
        Find similar decision points using FAISS k-NN around an existing
        DP's vector.
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Query</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-3 md:flex-row md:items-end"
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
          >
            <div className="flex-1">
              <label className="text-xs text-muted-foreground">
                Decision ID
              </label>
              <Input
                value={decisionId}
                onChange={(e) => setDecisionId(e.target.value)}
                placeholder="e.g. 11514545395_8"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">k</label>
              <Input
                type="number"
                min={1}
                max={200}
                value={k}
                onChange={(e) => setK(Number(e.target.value))}
                className="w-24"
              />
            </div>
            <Button type="submit" disabled={mutation.isPending || !decisionId}>
              {mutation.isPending ? "Searching…" : "Search"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {mutation.error && (
        <p className="text-destructive">
          Search failed: {(mutation.error as Error).message}
        </p>
      )}

      {mutation.data && (
        <ResultsList
          results={mutation.data.results}
          searchTimeMs={mutation.data.search_time_ms}
        />
      )}
    </div>
  );
}
