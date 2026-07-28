# Phase 5N Web Implementation Report

Updated: 2026-06-22

## Delivered Journey

`/?view=asset` is now a source-backed multi-panel workstation rather than a single price line plus taxonomy card.

- Asset routes default to `live-if-available` while cache and fixture remain explicit URL states.
- URL state retains symbol, asset class, interval, range, surface, chart type, bounded panels, comparison, and runtime mode.
- AAPL/MSFT/SPY/BTCUSDT/ETHUSDT expose isolated OHLCV and technical panels.
- Candlestick and line charts include source-backed volume and SMA/EMA overlays.
- RSI, MACD, realized volatility/drawdown, and normalized comparison panes are rendered through Lightweight Charts.
- Equity/ETF financial availability, exact-title symbol news, and crypto futures context are asset-appropriate.
- Retrieval time and last market observation time are visible separately.

## Product Layout

The asset route uses a dedicated two-column desktop shell: compact product navigation plus a full-width workstation. The redundant outer diagnostics rail is hidden because source truth is already present inside the workstation. At 900px and below the shell becomes one column; the runtime diagnostics banner is removed so the market object appears first.

## Important Fixes

1. Default asset routes previously selected cache mode and could display old cached/fixture fallback values.
2. Global `td { max-width: 18rem }` styling compressed the chart library's internal price cell to 288px despite a 1,096px shell. Finance-chart table internals are now isolated from app data-table CSS.
3. The volume overlay's price scale is hidden and the renderer performs settled resize/fit passes.
4. Chart controls gained a visible keyboard focus ring.
5. Mobile/tablet asset grids now use the full viewport width.
6. News matching now requires a bounded canonical symbol/name term in the title; incidental summary mentions are excluded.

## Primary Files

- `lib/symbol_intelligence.py`
- `lib/technical_analysis.py`
- `lib/api_contracts.py`
- `backend/api/app.py`
- `apps/web/src/components/FinanceChart.tsx`
- `apps/web/src/components/SymbolWorkstation.tsx`
- `apps/web/src/lib/product-routes.ts`
- `apps/web/src/lib/fixtures.ts`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`

