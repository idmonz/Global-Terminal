# Phase 5E.2 Checkpoint - Market Heatmap

Date: 2026-06-19

## Why This Checkpoint Exists

The user explicitly called out that the web app still lacked a Finviz-level market heatmap. Phase 5E.1 added real chart rendering, but Market Intelligence still needed a broad market-at-a-glance surface where size and color communicate cross-sectional context.

This checkpoint adds a clean-room heatmap foundation before the larger map-news-event fusion slice.

## Benchmark Evidence

Reviewed and captured:

- Finviz map: `https://finviz.com/map`
  - Headless capture reached a Cloudflare security check, so it was used as behavioral evidence from search result text only.
  - Search evidence: mouse wheel zoom, panning, and ticker detail interaction.
- TradingView stock heatmap: `https://www.tradingview.com/heatmap/stock/`
  - Capture: `review_workspace/phase5e2_benchmark_captures/tradingview-stock-heatmap.png`
  - Observed behavior: group by sector, rectangle size by market-cap-style metric, color by daily percentage change, visible legend and large/small tiles.
- TradingView heatmap widget docs: `https://www.tradingview.com/widget-docs/widgets/heatmaps/stock-heatmap/`
  - Capture: `review_workspace/phase5e2_benchmark_captures/tradingview-heatmap-widget-docs.png`
- NASA Worldview: `https://www.earthdata.nasa.gov/data/tools/worldview`
  - Capture: `review_workspace/phase5e2_benchmark_captures/nasa-worldview.png`
  - Used for the next map-news-event fusion design direction.
- Bloomberg Terminal product page: `https://professional.bloomberg.com/products/bloomberg-terminal/`
  - Capture: `review_workspace/phase5e2_benchmark_captures/bloomberg-terminal.png`
  - Used as a benchmark for dense data/news/chart/research workflows.

## Implementation

Python contract:

- `lib/market_intelligence.py`
  - Added clean-room `market_heatmap` rows.
  - Rows are synthetic deterministic fixtures; no Finviz/TradingView data is copied.
  - Each tile carries:
    - `symbol`
    - `label`
    - `sector`
    - `industry`
    - `market_cap_weight`
    - `daily_return_pct`
    - `tile_area_pct`
    - `color_bucket`
    - `provider`
    - `source`
    - `source_status`
    - `freshness`
    - `fetched_at`
    - `confidence`
    - `caveat`
    - `data_gap`
    - `not_financial_advice`
  - Summary now includes `heatmap_tile_count`.

Web:

- `apps/web/src/app/page.tsx`
  - Added `MarketHeatmapBoard`.
  - Market Intelligence now shows the heatmap before chart panels.
  - The heatmap uses sector grouping, size-weighted flex tiles, red/gray/green color buckets, and a visible legend.
- `apps/web/src/app/globals.css`
  - Added market heatmap layout, tile, legend, and mobile styles.
  - Mobile workspace rail is compacted into a shorter scrollable two-column rail so analysis content appears earlier.
- `apps/web/scripts/validate-runtime-ui.mjs`
  - Added markers so removing the heatmap renderer fails validation.

Tests:

- `tests/test_market_intelligence_contracts.py`
  - Asserts `market_heatmap` exists, has at least 20 rows, is non-advisory, fixture-labeled, and exposes expected size/color fields.

## Data Truth

- This is not live market data.
- The heatmap is a deterministic, synthetic fixture designed to prove product UX and contract shape.
- Live heatmap mode requires provider-backed index constituents, market caps, returns, freshness, and source rows.
- No broker execution, order routing, or directional advice is added.

## Visual Verification

Local production render checked with Headless Chrome/Edge fallback.

Screenshots:

- `dist/phase5e2-market-heatmap-screenshots/market-heatmap-desktop.png` - 1440 x 1400
- `dist/phase5e2-market-heatmap-screenshots/market-heatmap-mobile.png` - 390 x 3200
- `dist/phase5e2-market-heatmap-screenshots/market-heatmap-mobile-compact-rail.png` - 390 x 2600

Findings:

- Desktop heatmap is visible near the top of Market Intelligence.
- Mobile heatmap renders and the workspace rail is reduced into a shorter two-column scroll area, but further product work should still prioritize mobile navigation and workspace switching.

## Remaining Work

- Connect heatmap rows to live/free-first provider mode.
- Add index/ETF/crypto heatmap modes.
- Add hover/selection detail panel.
- Tie heatmap outliers to news, event graph, and research report sections.
- Continue Phase 5E.2 map-news-event fusion.
