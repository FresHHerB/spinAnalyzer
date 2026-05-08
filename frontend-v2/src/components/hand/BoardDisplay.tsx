import { cn } from "@/lib/utils";

const SUIT_COLORS: Record<string, string> = {
  h: "text-red-400",
  d: "text-red-400",
  s: "text-foreground",
  c: "text-foreground",
};

const SUIT_GLYPH: Record<string, string> = {
  h: "♥",
  d: "♦",
  s: "♠",
  c: "♣",
};

export function BoardDisplay({
  cards,
  size = "md",
}: {
  cards: string[];
  size?: "sm" | "md";
}) {
  return (
    <div
      className={cn(
        "flex gap-2",
        size === "sm" ? "text-base" : "text-2xl font-semibold",
      )}
    >
      {cards.map((card, i) => (
        <CardChip key={`${card}-${i}`} card={card} size={size} />
      ))}
    </div>
  );
}

function CardChip({
  card,
  size,
}: {
  card: string;
  size: "sm" | "md";
}) {
  const rank = card[0];
  const suit = card[1];
  return (
    <div
      className={cn(
        "inline-flex items-center justify-center rounded border bg-card shadow-sm",
        size === "sm" ? "h-8 w-7 text-sm" : "h-12 w-10 text-xl",
        SUIT_COLORS[suit] ?? "",
      )}
    >
      <span className="leading-none">
        {rank}
        {SUIT_GLYPH[suit] ?? suit}
      </span>
    </div>
  );
}
