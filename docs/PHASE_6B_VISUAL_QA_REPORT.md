# Phase 6B Visual QA Report

Updated: 2026-07-01

## Harness

`npm --prefix apps/web run visual:phase6b`

Tested environments:

- online: web 3045 / API 8004;
- forced stale: web 3046 / API 8005 with zero freshness allowance;
- controlled API-invalid offline: web 3047 / API 8999.

## Online Evidence

- 333 rows and 333 heatmap tiles;
- 333 classified rows: 60 local, 273 provider;
- 60 reviewed industry rows;
- 11 canonical sector groups after a visual defect exposed duplicate
  `Technology`/`Information Technology` labels;
- 2 visible refresh-history jobs;
- `market_snapshot.v2`;
- final first useful paint: 1,724 ms desktop and 1,158 ms mobile;
- final hierarchy interaction: 60 ms;
- AAPL workstation round trip preserved query, selected symbol, size, and color;
- unknown symbol did not leak Apple identity;
- no page-level overflow or browser console/page errors.

## Stale And Offline

- forced stale retained 333 rows and showed amber stale truth;
- stale first useful paint: 2,370 ms desktop / 1,503 ms mobile;
- controlled offline showed 30 deterministic fixture rows, runtime unreachable,
  unmaterialized snapshot, and no fake refresh history;
- offline first useful paint: 1,877 ms desktop / 1,215 ms mobile.

## Personally Inspected

- `review_workspace/phase6b_visual_online/market-map-desktop.png`
- `review_workspace/phase6b_visual_online/market-map-mobile.png`
- `review_workspace/phase6b_visual_online/market-map-hierarchy.png`
- `review_workspace/phase6b_visual_stale/market-map-desktop.png`
- `review_workspace/phase6b_visual_offline/market-map-desktop.png`

The desktop first viewport is dense but readable. Mobile is very long because 333
tiles remain inspectable; it has no document overflow. A future virtualization or
mobile top-N mode may improve scan speed without hiding breadth.
