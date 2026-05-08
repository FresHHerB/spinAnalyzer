import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SizingBucket } from "@/lib/api-types";

const BUCKET_ORDER = [
  "tiny_le33",
  "half_pot",
  "two_thirds",
  "pot",
  "overbet",
];

interface Row {
  bucket: string;
  flop: number;
  turn: number;
  river: number;
}

export function SizingHistogramChart({ buckets }: { buckets: SizingBucket[] }) {
  const map = new Map<string, Row>();
  for (const b of BUCKET_ORDER) {
    map.set(b, { bucket: b, flop: 0, turn: 0, river: 0 });
  }
  for (const b of buckets) {
    const row = map.get(b.bucket);
    if (!row) continue;
    if (b.street === "flop") row.flop = b.count;
    else if (b.street === "turn") row.turn = b.count;
    else if (b.street === "river") row.river = b.count;
  }
  const data: Row[] = Array.from(map.values());

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis dataKey="bucket" stroke="hsl(var(--muted-foreground))" />
        <YAxis stroke="hsl(var(--muted-foreground))" />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
          }}
        />
        <Legend />
        <Bar dataKey="flop" fill="hsl(220, 70%, 60%)" />
        <Bar dataKey="turn" fill="hsl(160, 70%, 50%)" />
        <Bar dataKey="river" fill="hsl(40, 80%, 60%)" />
      </BarChart>
    </ResponsiveContainer>
  );
}
