import { Outlet, createRootRoute } from "@tanstack/react-router";
import { Sidebar } from "@/components/layout/Sidebar";

export const Route = createRootRoute({
  component: () => (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  ),
});
