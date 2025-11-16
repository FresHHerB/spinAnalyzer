# SpinAnalyzer v2.0 - Frontend

React + TypeScript frontend for the SpinAnalyzer Pattern Matching Engine.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool & dev server
- **TailwindCSS** - Styling
- **React Router** - Routing
- **TanStack Query** - Data fetching & caching
- **Axios** - HTTP client
- **Zustand** - State management (if needed)
- **Lucide React** - Icons
- **Recharts** - Charts (for future stats)

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env if API is not on localhost:8000
```

### 3. Start Dev Server

```bash
npm run dev
```

Frontend will be available at http://localhost:3000

API proxy configured: `/api/*` -> `http://localhost:8000/*`

### 4. Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable components
│   │   ├── Layout.tsx
│   │   ├── VillainCard.tsx
│   │   └── ResultsTable.tsx
│   ├── pages/            # Route pages
│   │   ├── Dashboard.tsx
│   │   ├── Search.tsx
│   │   └── VillainProfile.tsx
│   ├── services/         # API client
│   │   └── api.ts
│   ├── types/            # TypeScript types
│   │   └── index.ts
│   ├── hooks/            # Custom hooks (future)
│   ├── store/            # Zustand store (future)
│   ├── App.tsx           # App root with routes
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles + Tailwind
├── public/               # Static assets
├── index.html            # HTML template
├── vite.config.ts        # Vite configuration
├── tailwind.config.js    # Tailwind configuration
├── tsconfig.json         # TypeScript configuration
└── package.json
```

## Features Implemented

### ✅ Dashboard
- Villain cards with stats
- Summary statistics (total villains, DPs, vectors)
- Quick links to villain profiles

### ✅ Search
- Query Builder with filters:
  - Villain selection
  - Street (preflop/flop/turn/river)
  - Position (BTN/BB/IP/OOP)
  - Pot size range (BB)
  - Results count (k)
- Results table with all decision point details
- Search time display

### ✅ Villain Profile
- Detailed villain statistics
- Street distribution
- Position distribution
- Top actions with progress bars
- Pot size distribution
- SPR distribution

### ✅ Layout
- Responsive navigation
- Health status indicator
- API connection monitoring
- Clean, professional UI

## API Integration

All API calls are typed and use TanStack Query for:
- Automatic caching
- Background refetching
- Loading states
- Error handling

See `src/services/api.ts` for all available endpoints.

## Development

### Adding a New Page

1. Create component in `src/pages/YourPage.tsx`
2. Add route in `src/App.tsx`
3. Add navigation link in `src/components/Layout.tsx` (if needed)

### Adding a New API Call

1. Add types in `src/types/index.ts`
2. Add function in `src/services/api.ts`
3. Use with `useQuery` or `useMutation` in components

### Styling

Uses TailwindCSS with custom utilities:
- `.card` - White card with shadow
- `.btn` - Button base
- `.btn-primary` - Primary button
- `.btn-secondary` - Secondary button
- `.input` - Form input
- `.select` - Form select
- `.badge` - Small badge/tag

Custom colors in `tailwind.config.js`:
- `primary.*` - Blue shades
- `poker.*` - Poker-themed colors

## Scripts

```bash
npm run dev      # Start dev server (port 3000)
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## Troubleshooting

### Port 3000 Already in Use

Change port in `vite.config.ts`:
```ts
server: {
  port: 3001, // or any other port
}
```

### API Connection Issues

1. Check backend is running: http://localhost:8000/health
2. Verify VITE_API_URL in `.env`
3. Check browser console for CORS errors

### Type Errors

Ensure types in `src/types/index.ts` match backend Pydantic models.

## Future Enhancements

- [ ] Hand Replayer component
- [ ] Advanced filters (board texture, draws)
- [ ] Charts and visualizations (Recharts)
- [ ] Export results (CSV, JSON)
- [ ] Saved queries
- [ ] Dark mode
- [ ] Mobile-optimized UI

## Notes

- Frontend is designed to match backend API exactly
- All types are derived from backend Pydantic models
- Uses TanStack Query for optimal data fetching
- Fully typed with TypeScript
- Responsive design (mobile-first)

---

**Version:** 2.0.0
**Status:** MVP Complete
**Next:** Advanced features & visualizations
