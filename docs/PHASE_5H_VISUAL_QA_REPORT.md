# Phase 5H Visual QA Report

Updated: 2026-06-20

## Method

The required in-app Browser bootstrap returned unavailable. The first installed-browser fallback was Headless Edge, which exited with code 13 in this Windows session. `playwright-core` was therefore added as a development-only QA dependency and used with the installed production Chrome executable. No browser binary was downloaded.

The QA script is reproducible:

```powershell
npm.cmd --prefix apps/web run visual:phase5h
```

## Personally Inspected Evidence

Files are under `review_workspace/phase5h_visual/`.

- `global-risk-map-desktop.png`: live-if-available runtime, 29 source-backed markers observed, USGS provider coordinates and source link visible.
- `global-risk-map-cache-desktop.png`: deterministic cache/proxy path, 8 visible chokepoints.
- `global-risk-map-cache-mobile.png`: 390x844 product view; the map is visible in the first viewport after mobile compaction.
- `global-risk-map-fallback.png`: renderer fallback keeps 8 positioned events and an event inspector without Leaflet tiles.
- `baseline-map-desktop.png`: pre-change evidence showing the small diagnostic map and repository-wide metadata dominance.

## Automated Evidence

Final cache-mode run:

- desktop: state `ready`, 8 markers, 15 loaded tiles, map 1023x642;
- mobile: state `ready`, 8 markers, 15 loaded tiles, map 358x567;
- fallback: state `fallback`, 8 markers, map 623x514;
- canonical state: layer, `7d` timeline, `previous_24h` compare, and selected marker persisted in the URL;
- browser console errors: 0.

## Defects Found And Corrected

1. Contract diagnostics, 20-workspace navigation, and repository-wide gap counts dominated the map route. Replaced with a dedicated map product shell.
2. The mobile symbol form and status cards pushed the map below the first viewport. The map route now uses a compact header, horizontal product navigation, concise runtime boundary, and visible first-viewport map.
3. Leaflet import/tile failure had no useful product path. Added an explicit coordinate-grid fallback with event selection.
4. Dense provider results had no collision handling. Added first-party grid density clustering above 60 rows.
5. URL state did not own all map controls. Layers, timeline, event, compare, runtime, and fallback state are now shareable.

## Benchmark Comparison

Adopted behavior-only principles from WorldMonitor/worldview include map-first hierarchy, persistent controls, selected-event source context, timeline state, mobile popup/drawer behavior, and useful failure states. No AGPL/NASA code, CSS, branded asset, or map visual was copied.

## Residual Visual/Product Risk

Historical compare overlays, marker spiderfying at high zoom, richer weather rendering, saved map views, and live flight/AIS density were not proven because the required provider/history data is unavailable.

