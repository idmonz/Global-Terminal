# Phase 5I Visual QA Report

Updated: 2026-06-20

## Method

The repository `playwright-core` harness controlled installed production Chrome against `next start` and the local FastAPI. The script is:

```powershell
npm.cmd --prefix apps/web run visual:phase5i
```

## Inspected Evidence

Files under `review_workspace/phase5i_visual/`:

- `baseline-screener-diagnostics.png`: old contract diagnostics surface.
- `market-map-live-desktop.png`: 60-row live/cache product.
- `market-map-live-mobile.png`: selected-sector mobile product.
- `market-map-fixture-fallback.png`: deterministic fixture route.

## Automated Assertions

- desktop: 60 rows, 60 tiles, 60 table rows, 50 scatter points, heatmap 1031x782;
- mobile selected sector: 5 rows/tiles, heatmap 358x664;
- fixture fallback: 30 rows/tiles/scatter points, heatmap 687x649;
- URL retained sector, sort, direction, selected symbol, compare symbol, asset class, freshness, and runtime mode;
- browser console errors: 0.

## Defects Found And Corrected

1. Contract diagnostics owned the screener route. Added a product-first route.
2. Static heatmap rows were presented as the only discovery surface. Wired the existing 60-symbol runtime.
3. Missing values could be visually confused with zero. Added rank eligibility and missing-last sorting.
4. Taxonomy and price freshness were conflated. Split their status fields.
5. Mobile navigation hid the active route off-screen. Active Market Map now sorts first in the mobile rail.
6. Mobile screenshot retained post-click scroll. QA now resets to the first viewport before capture.

## Residual Risk

The flex hierarchy is useful but not a full squarified treemap. Broad provider latency is about one minute on a cold fetch, mitigated by the 10-minute cache. Only AAPL currently has a verified equity workstation link.

