import { Link, useRouterState } from "@tanstack/react-router";
import {
  BarChart3,
  Layers,
  PlayCircle,
  Search,
  Upload,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { to: "/", label: "Dashboard", icon: BarChart3 },
  { to: "/villains", label: "Villains", icon: Users },
  { to: "/search/by-decision", label: "Search by DP", icon: Search },
  { to: "/search/by-action-path", label: "Search by line", icon: Layers },
  { to: "/search/by-spot-builder", label: "Spot builder", icon: PlayCircle },
  { to: "/upload", label: "Upload", icon: Upload },
];

export function Sidebar() {
  const { location } = useRouterState();
  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-border bg-card px-3 py-6">
      <div className="px-3 pb-6">
        <h1 className="text-xl font-bold tracking-tight">SpinAnalyzer</h1>
        <p className="text-xs text-muted-foreground">v2 — pattern engine</p>
      </div>
      <nav className="flex flex-col gap-1">
        {items.map(({ to, label, icon: Icon }) => {
          const active = location.pathname === to ||
            (to !== "/" && location.pathname.startsWith(to));
          return (
            <Link
              key={to}
              to={to}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-secondary text-secondary-foreground"
                  : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
