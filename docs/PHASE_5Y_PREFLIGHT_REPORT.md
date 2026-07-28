# Phase 5Y Preflight Report

Updated: 2026-07-01

## Phase Contract

Phase 5Y targets one complete journey:

`runtime truth -> map layers -> select event -> reporting and provenance -> market transmission -> return to map`

The slice must improve source-backed map intelligence, not merely add another schema or rearrange diagnostics.

## Baseline Gates

- Full Python regression: PASS with the existing Starlette `httpx` deprecation warning and two cointegration collinearity warnings.
- Web fixture/runtime validation: PASS, 27 fixtures.
- ESLint: PASS.
- Next.js production build: PASS.
- `npm audit --audit-level=high`: PASS, zero vulnerabilities.
- Pre-edit release ZIP: PASS, 1,490 packaged files plus manifest.
- External archive audit: PASS, 28 archives, 51,305 entries, 39,622 text candidates, 10,596,233 indexed lines, 249,590 symbols, zero read errors.
- User-required external evidence paths: 42 of 42 present.

## Baseline Runtime Evidence

`GET /api/war-room-map?include_runtime=true` returned:

- 37 coordinate-backed markers;
- 29 `live/fresh` USGS markers;
- 8 `proxy/static` chokepoints;
- 34 layer contracts;
- no live AIS, flight, sanctions, or vessel claim.

`GET /api/news?include_runtime=true` returned 40 normalized source-labeled news rows, but the fusion contract exposed only one `high_severity_feed` row.

## Baseline Visual Result

Evidence: `review_workspace/phase5u_phase5y_baseline/`

- Cache desktop: map ready, 37 markers, 24 loaded tiles, no horizontal overflow.
- Cache mobile: map ready, 37 markers, 8 loaded tiles, no horizontal overflow.
- Fixture and fallback desktop: map began at 457 px, failing the existing 430 px map-first threshold.
- The selected USGS event showed zero related reporting and zero market-transmission rows.
- The long-running Next process was serving an older production build, so the final Phase 5Y proof must use freshly built, separately verified process IDs and ports.

## Confirmed Product Defects

1. `map_news_event_fusion` prioritizes a one-row high-severity subset over the complete normalized news feed.
2. Event-link expansion includes edges attached to shared taxonomy nodes, which can present unrelated events as direct evidence.
3. Connected assets and reporting are built only for one contract-selected marker, so changing the map selection can leave the inspector empty even when graph context exists.
4. The map first viewport spends too much vertical space on replay framing in fixture mode.
5. Current event regions are often `Global`, limiting geographic news matching even when the event title contains a place.

## Clean-Room Boundary

- WorldMonitor, OpenBB, OpenStock, and OctoBot remain AGPL behavior-only references.
- NASA Worldview remains behavior-only pending separate legal review.
- Missing-license and screenshot references remain design/behavior evidence only.
- No external source, visual asset, font, dataset, or CSS is copied into the runtime product.
- The implementation will use project-native Python, TypeScript, React, Leaflet, and existing source-backed providers.

## Done Criteria

Phase 5Y can pass only when:

1. every selected marker gets a bounded, direct event context;
2. news matching exposes exact/region/keyword/fallback methods without implying false causality;
3. market transmission labels inferred taxonomy separately from source-backed market data;
4. desktop/mobile online and controlled-offline screenshots are captured and inspected;
5. the map is nonblank, marker-ready, and above the first-viewport threshold;
6. AAPL and BTCUSDT routes do not regress;
7. focused and full Python/web/release gates pass.

