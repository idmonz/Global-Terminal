# Phase 5H Web Implementation Report

Updated: 2026-06-20

## Delivered Journey

`Market Home -> War Map -> layer/timeline -> event -> primary source/news/asset context`

`/?view=war-room-map` now renders a product-first `GlobalRiskMapProduct` instead of the repository-wide contract diagnostics layout. The first desktop viewport is a large Leaflet map with compact runtime truth, layer controls, event stream, and selected-event inspector.

## Product Behavior

- Runtime defaults to `live-if-available` for the map route and retains explicit `fixture`, `cache`, and renderer-fallback modes.
- URL state owns `mode`, `layers`, `timeline`, `compare`, and `event`.
- Selected events expose provider, source/freshness state, coordinate method, confidence, caveat, data gap, and primary source URL.
- Related reporting requires source URL, event ID, or exact region evidence; unrelated news is not used as filler.
- Asset links require graph IDs already attached to the event. Only supported AAPL/BTCUSDT routes become clickable product links.
- More than 60 coordinate rows use a first-party grid-density cluster. The event list retains every row.
- Renderer import/error can be forced with `mapMode=fallback`; event coordinates remain useful in an accessible grid fallback.

## Runtime Composition

- USGS earthquakes: real keyless runtime path with source-backed `usgs_geojson` coordinates.
- Public RSS/GDELT aggregate: real/cache/stale rows when providers succeed.
- Static chokepoints: retained and clearly labeled `proxy/static` with low confidence.
- OpenSky: credentials are configured, but the observed OAuth probe returned 401. No flight row is claimed live.
- AIS, sanctions, and other premium/credentialed layers remain unavailable unless a successful provider fetch proves otherwise.

## Additional Runtime Fixes

- Fixed `build_api_news_dashboard_payload()` evaluating a pandas DataFrame as a boolean.
- Added the manifest-declared but missing `/api/research-report` FastAPI route.
- Installed the optional FastAPI package in the current environment; base application dependencies remain separated by `requirements-api.txt`.

## Main Files

- `lib/war_room_map.py`
- `lib/event_stream.py`
- `lib/war_room.py`
- `lib/map_news_event_fusion.py`
- `lib/api_contracts.py`
- `backend/api/app.py`
- `apps/web/src/app/page.tsx`
- `apps/web/src/components/LeafletWarMap.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/scripts/capture-phase5h.mjs`

## Honest Remaining Gaps

Compare state is URL-stable but does not yet draw persisted historical snapshots. Weather is represented only where current contracts have meaningful rows. Live AIS, successful OpenSky flights, sanctions, durable map history, saved views, alerts, and broad event-to-instrument coverage remain future work.

