import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ResultsList } from "@/components/search/ResultsList";

const STREETS = ["preflop", "flop", "turn", "river"];
const POSITIONS_POSTFLOP = ["IP", "OOP"];
const POSITIONS_PREFLOP = ["BTN", "BB"];

export const Route = createFileRoute("/search/by-spot-builder")({
  component: SearchBySpotBuilderPage,
});

function SearchBySpotBuilderPage() {
  const villains = useQuery({
    queryKey: ["villains"],
    queryFn: api.listVillains,
  });

  const [villain, setVillain] = useState("");
  const [street, setStreet] = useState("flop");
  const [position, setPosition] = useState("OOP");
  const [boardCards, setBoardCards] = useState("Kh 9d 4c");
  const [potBb, setPotBb] = useState(10);
  const [stackBb, setStackBb] = useState(50);
  const [betPct, setBetPct] = useState<number | "">(66);
  const [aggressor, setAggressor] = useState<"hero" | "villain" | "">("");
  const [k, setK] = useState(50);

  const positions = street === "preflop" ? POSITIONS_PREFLOP : POSITIONS_POSTFLOP;

  const mutation = useMutation({
    mutationFn: () =>
      api.searchBySpot({
        villain_name: villain,
        street,
        villain_position: position,
        board_cards: boardCards.trim() ? boardCards.trim().split(/\s+/) : [],
        pot_bb: potBb,
        eff_stack_bb: stackBb,
        bet_size_pot_pct: betPct === "" ? null : Number(betPct),
        aggressor: aggressor === "" ? null : aggressor,
        k,
      }),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold">Spot builder</h2>
      <p className="text-muted-foreground">
        Construct a synthetic decision point and find the closest matches in
        the villain's vector index.
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Spot</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 md:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
          >
            <Field label="Villain">
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={villain}
                onChange={(e) => setVillain(e.target.value)}
                required
              >
                <option value="">— select —</option>
                {villains.data?.villains.map((v) => (
                  <option key={v.name} value={v.name}>
                    {v.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Street">
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={street}
                onChange={(e) => {
                  setStreet(e.target.value);
                  setPosition(
                    e.target.value === "preflop" ? "BTN" : "OOP",
                  );
                }}
              >
                {STREETS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Villain position">
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={position}
                onChange={(e) => setPosition(e.target.value)}
              >
                {positions.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Aggressor">
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={aggressor}
                onChange={(e) =>
                  setAggressor(e.target.value as "hero" | "villain" | "")
                }
              >
                <option value="">none</option>
                <option value="hero">hero</option>
                <option value="villain">villain</option>
              </select>
            </Field>
            <Field label="Board cards (space-separated)">
              <Input
                value={boardCards}
                onChange={(e) => setBoardCards(e.target.value)}
                placeholder="Kh 9d 4c"
                className="font-mono"
              />
            </Field>
            <Field label="Pot (BB)">
              <Input
                type="number"
                min={0}
                step={0.5}
                value={potBb}
                onChange={(e) => setPotBb(Number(e.target.value))}
              />
            </Field>
            <Field label="Eff stack (BB)">
              <Input
                type="number"
                min={0}
                value={stackBb}
                onChange={(e) => setStackBb(Number(e.target.value))}
              />
            </Field>
            <Field label="Bet size (% pot)">
              <Input
                type="number"
                min={0}
                max={500}
                value={betPct}
                onChange={(e) =>
                  setBetPct(e.target.value === "" ? "" : Number(e.target.value))
                }
                placeholder="66"
              />
            </Field>
            <Field label="k">
              <Input
                type="number"
                min={1}
                max={500}
                value={k}
                onChange={(e) => setK(Number(e.target.value))}
              />
            </Field>
            <div className="flex items-end">
              <Button type="submit" disabled={!villain || mutation.isPending}>
                {mutation.isPending ? "Searching…" : "Search"}
              </Button>
            </div>
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

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="text-xs text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}
