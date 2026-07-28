# Phase 6E Progressive Delivery Contract

Updated: 2026-07-03

## Delivery Shape

The compatibility `chart` contract remains available. Phase 6E adds:

- `summary`: identity, quote, market/source clock, no returned history;
- `chart-core`: exact candles, volume, displayed overlays, no duplicated raw
  history or lower panels;
- `technicals`: compact calculation summary and indicator charts;
- `financials`, `news`, `sources`, `comparison`: exact on-demand panels.

Routes remain:

```text
GET /api/symbol-workstation/{symbol}/summary
GET /api/symbol-workstation/{symbol}/panels/{panel}
```

All deliveries retain exact identity, cache partition, source register,
freshness, caveat, data gap, and non-advisory labels. Unknown symbols return
404 and are never replaced.

## Browser Boundary

The web client calls `/api/runtime/...`. The Next route handler uses only the
server-side `GLOBAL_TERMINAL_API_BASE_URL`, a fixed allowlist, GET-only access,
15-second timeout, and forwarded ETag/cache headers. A browser cannot choose an
upstream host.

## Cache Semantics

ETags exclude only generated/elapsed clock fields. Substantive identity, quote,
history, source, or calculation changes alter the ETag. Revalidation of
unchanged chart-core data returns `304` with zero response bytes.

## Watchlist Boundary

Advanced metrics are calculated from an existing exact-symbol `1d / 3mo`
history cache. The calculation function performs zero provider calls. Missing
history or fundamentals remain `partial` or `unavailable`; mode, sort, and group
changes are client-only.
