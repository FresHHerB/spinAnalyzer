# SpinAnalyzer v2 — Frontend

React + TypeScript + Vite SPA for the v2 search engine.

## Stack

- **Vite** + React 18 + TypeScript 5
- **TanStack Router** (file-based routing, manual `routeTree.gen.ts`)
- **TanStack Query** for data fetching/caching
- **Tailwind CSS** + shadcn-style primitives (vendored)
- **Recharts** for sizing histograms
- **Vitest** + **@testing-library/react** for unit tests
- **Playwright** for end-to-end smoke tests

## Dev

```bash
npm install
npm run dev          # http://localhost:5173 (proxies /api → :8000)
```

## Test

```bash
npm run test         # Vitest unit
npm run test:watch   # Vitest watch
npm run e2e          # Playwright (boots dev server)
```

## Type generation from OpenAPI

`src/lib/api-types.ts` is hand-written. To regenerate from a running
backend:

```bash
npm run gen-api
```

## Build

```bash
npm run build
npm run preview
```

## Routes

| Path | Component |
|---|---|
| `/` | Dashboard (KPIs + villain table) |
| `/villains` | Villain card grid |
| `/villains/$name` | Profile + stats + sizing histogram |
| `/hands/$id` | Hand replayer (board + timeline + DP cards) |
| `/search/by-decision` | k-NN search around an existing DP |
| `/search/by-action-path` | exact-match filter on (villain, street, path) |
| `/search/by-spot-builder` | Mode A — synth DP from picker fields |
| `/upload` | dropzone + WebSocket progress |
