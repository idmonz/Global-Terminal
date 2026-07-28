# Phase 5C Runtime Renderer Foundation Spec

Updated: 2026-06-19

Phase 5C begins the corrective implementation after Phase 5B. It does not complete the full terminal vision yet. This phase now has three foundations: visible runtime-mode boundaries, hardened fallback charts, and a first real interactive Leaflet map renderer for War Map.

## Implemented In This Slice

### Runtime Mode Boundary

Files:

- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`

Added:

- `RuntimeMode = fixture | cache | live-if-available`.
- `mode` query parameter parsing.
- Runtime mode selector in the top command form.
- Workspace rail links preserve selected runtime mode.
- Runtime banner above every workspace summary.
- Right rail runtime explanation.
- Provider strip runtime mode label.

Important limitation:

- The static Next.js shell still loads deterministic fixtures from `static/api-fixtures`.
- `cache` and `live-if-available` started as explicit UI/API boundary modes. On 2026-06-19, the selected workspace can now optionally fetch the local API when `GLOBAL_TERMINAL_API_BASE_URL` or `NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL` is configured.
- If the optional API base URL is absent, returns an explicit `runtime-fallback` warning and keeps static fixtures. If the API fails or returns an invalid envelope, it falls back to fixtures with an error label. Failed providers must become cached/stale/unavailable/error/fallback states, not fake live rows.


### Optional Runtime API Loader

Files:

- `apps/web/src/lib/contracts.ts`
- `apps/web/src/lib/fixtures.ts`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/scripts/validate-runtime-ui.mjs`

Added on 2026-06-19:

- Shared `RuntimeMode` definitions moved into the contract layer.
- `loadRuntimeFixture()` attempts the optional local API for supported workspaces when mode is `cache` or `live-if-available`.
- `live-if-available` calls API routes with `include_runtime=true`.
- `cache` calls the optional API with `include_runtime=false` for the selected route when the local API base URL is configured.
- When no API base URL is configured, or a fetch/validation failure occurs, the UI shows `runtime-fallback` and keeps the deterministic fixture instead of implying live data.
- The runtime fallback warning is visible in the main workspace and right rail.

Configuration:

```powershell
$env:GLOBAL_TERMINAL_API_BASE_URL="http://127.0.0.1:8000"
npm.cmd --prefix apps/web run start -- -p 3000
```

The variable is intentionally server-side. `NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL` is also accepted for local experiments, but server-side `GLOBAL_TERMINAL_API_BASE_URL` is preferred so API location does not get bundled into browser JavaScript.

### Native Chart Fallback Hardening

Files:

- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`

Added:

- `ChartAxes` helper.
- `paddedDomain` helper.
- short number/date axis labels.
- zero baseline for bar charts.
- negative-value-safe bar rendering.
- independent normalization for multi-series charts with mismatched units.
- visible series labels.
- CSS for gridlines, axes, zero line, axis labels, and stable responsive chart height.

Important limitation:

- This is still a first-party fallback renderer, not a TradingView/Koyfin-grade chart engine.
- The next slice should either adopt a reviewed financial chart library or implement a more complete first-party renderer.


### Leaflet War Map Renderer

Files:

- `apps/web/package.json`
- `apps/web/package-lock.json`
- `apps/web/src/components/LeafletWarMap.tsx`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/scripts/validate-runtime-ui.mjs`

Added on 2026-06-19:

- Installed `leaflet` and `@types/leaflet`.
- Added a client-only, SSR-safe `LeafletWarMap` component with dynamic `import("leaflet")` to avoid server-side `window` errors.
- Replaced the primary War Map schematic panel with an interactive Leaflet map using OpenStreetMap tiles and attribution.
- Added marker pan/zoom, marker popups, marker inspector, map-linked event list, layer toggles, and timeline filter state.
- Every displayed marker keeps provider, source status, confidence, coordinate method/status, source URL, caveat, and data-gap fields visible.
- Disabled/unavailable layers remain disabled; live AIS/flight/sanctions are not claimed.

Renderer decision:

- Leaflet was chosen over MapLibre for this slice because it gives the fastest credible product upgrade for pan/zoom/tile/marker/popup behavior while keeping implementation scope small.
- MapLibre remains a later candidate for vector tiles, clustering, heatmaps, and heavier worldview-style layer composition.

Official references:

- Leaflet API reference: `https://leafletjs.com/reference.html`
- Leaflet license: `https://github.com/Leaflet/Leaflet/blob/main/LICENSE`

### Regression Guards

Files:

- `apps/web/scripts/validate-runtime-ui.mjs`
- `apps/web/package.json`

Added:

- `npm test` now runs both fixture validation and runtime/chart UI marker validation.
- The new validator checks that runtime modes, `RuntimeModeBanner`, `ChartAxes`, `paddedDomain`, and runtime/chart CSS markers remain present.
- It also fails if generated literal newline escape tokens are left in source files.

## Verification

Passed on 2026-06-19:

```powershell
npm.cmd --prefix apps/web test
npm.cmd --prefix apps/web run lint
npm.cmd --prefix apps/web run build
```

Results:

- 15 `phase_2b.v1` fixtures validated.
- Runtime mode boundary, optional runtime loader, native chart fallback markers, and Leaflet War Map markers validated.
- ESLint passed.
- Next.js production build passed.
- Local production HTTP marker checks passed on `http://127.0.0.1:3004/?view=market-intelligence&mode=live-if-available` and `http://127.0.0.1:3005/?view=market-intelligence&mode=live-if-available` with `Runtime Boundary`, `Runtime fallback`, `GLOBAL_TERMINAL_API_BASE_URL`, and `Market Intelligence` present.
- Headless Edge screenshots were generated:
  - `dist/phase5c-screenshots/market-runtime-desktop.png` 1440x1100
  - `dist/phase5c-screenshots/market-runtime-mobile.png` 390x1100
  - `dist/phase5c-screenshots/war-map-runtime-desktop.png` 1440x1100
- The sandbox image viewer could not open the moved `Global Terminal` path, so screenshots were verified by file creation, image dimensions, and pixel-color sampling.
- Leaflet War Map screenshots were generated:
  - `dist/phase5c-leaflet-map-screenshots/war-room-map-leaflet-desktop.png` 1440x1200, nonblank sampled colors
  - `dist/phase5c-leaflet-map-screenshots/war-room-map-leaflet-mobile.png` 390x1200, nonblank sampled colors

## Current Data Truth

This slice does not turn fixture data into live data by itself. It adds the optional bridge that can fetch the local API when configured and otherwise keeps fixture fallback explicit.

Current visible truth remains:

- `market-intelligence`: mostly `fixture` / `inferred/proxy` in static fixture mode.
- `equity-intelligence`: `fixture`, `inferred/proxy`, `provider-required` in static fixture mode.
- `crypto-intelligence`: `fixture`, `inferred/proxy` in static fixture mode.
- `war-room-map`: `fixture`, `missing-key`, `proxy/static`, `unavailable` in static fixture mode.

The new runtime UI and loader make these boundaries clearer and prevent `live-if-available` from silently behaving like live data when the optional backend is not configured.

## Remaining Phase 5C Work

The next implementation slice should not redo this work. It should continue from here.

Priority order:

1. Start the optional FastAPI backend or a deterministic local mock and prove one major workspace can show `runtime-api` rows when the API succeeds.
2. Add provider-failure tests proving no fake live rows appear.
3. Decide and implement the first real financial chart foundation, preferably a reviewed finance chart package after license/docs review.
4. Deepen the Leaflet map toward clustering, source-linked news rows, and better layer grouping after runtime rows are available.
5. Capture desktop/mobile visual screenshots for every customer-facing renderer change.

## External And License Stance

No external source code was copied.

- WorldMonitor/OpenBB/OpenAlice/OpenStock remain AGPL behavior-only.
- worldview remains NASA behavior-only.
- BB-Terminal remains blocked/direct-copy-not-used.
- FinanceDatabase remains MIT schema/taxonomy reference only.
- Leaflet is now installed for the first interactive War Map renderer. TradingView Lightweight Charts and MapLibre remain candidate dependencies for later reviewed adoption.

## Non-Goals

Not implemented in this slice:

- New chart npm dependency.
- Successful live provider rows through the optional API are not yet proven end to end.
- Screener workspace.
- Portfolio quant workspace.
- Financial statement workspace.
- Options/GEX workspace.
- Research report generator.
- Auth, billing, accounts, hosted persistence, broker execution, order routing, paid dependency, or financial advice.

