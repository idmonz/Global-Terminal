# Phase 5N Visual QA Report

Updated: 2026-06-22

## Method

The in-app Browser could not initialize because required sandbox metadata was absent. The repository-approved fallback used installed production Chrome and `playwright-core` against production Next.js and local FastAPI. Harness: `apps/web/scripts/capture-phase5n.mjs`.

## Final Assertions

- exact symbol and no cross-symbol history substitution;
- candlestick/line URL persistence;
- nonzero candles, volume, technical points, and canvas pixel samples;
- desktop chart shell at least 760px and internal price plot at least 78% of shell width;
- mobile internal price plot at least 70% of shell width;
- comparison overlap and exact-news success;
- fixture empty-news, chart fallback, and unknown-symbol states;
- visible keyboard focus;
- no document overflow;
- zero console/page errors.

## Final Evidence

| Surface | Key evidence |
| --- | --- |
| AAPL desktop | 64 OHLCV rows, 64 candles/volume, 188 line/overlay points, 5 exact-title news rows, 64 comparison overlap, 1,096px chart shell, 1,018px price plot |
| MSFT desktop line | 64 rows, 4 news rows, 64 overlap, line URL state |
| SPY ETF | fund-profile context, 64 rows, 2 news rows, 64 overlap |
| BTCUSDT | 121 rows/candles/volume, 416 points, 4 news rows, 121 overlap, funding/basis/open-interest context |
| Tablet 768 | 740px workstation, 493px chart, no overflow |
| Mobile 390 | 369px workstation, 351px chart, 266px price plot, no overflow |
| Fixture | 48 synthetic rows, fixture market clock, zero fabricated news |
| Unknown/fallback | explicit unknown-symbol and chart-fallback states |

## Personally Inspected Captures

- `review_workspace/phase5n_visual/aapl-live-candlestick-desktop.png`
- `review_workspace/phase5n_visual/aapl-live-full-page.png`
- `review_workspace/phase5n_visual/btcusdt-derivatives-desktop.png`
- `review_workspace/phase5n_visual/aapl-live-tablet.png`
- `review_workspace/phase5n_visual/ethusdt-live-mobile.png`
- fixture, fallback, and unknown captures in the same directory.

The final desktop chart occupies the full available plot width. The full-page capture shows the indicator tape, RSI/MACD/risk/comparison panes, financial availability, exact-title news, and source caveats in one coherent workstation.

