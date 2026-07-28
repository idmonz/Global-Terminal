# Phase 5G Product Contract

## Required Journey

`/` -> AAPL -> Home -> BTCUSDT -> unknown symbol.

Canonical state:

- `/?view=asset&symbol=AAPL&assetClass=equity&timeframe=1D`
- `/?view=asset&symbol=BTCUSDT&assetClass=crypto&timeframe=1D`

## Market Home

Show market tape, AAPL/BTCUSDT entry points, market discovery/heatmap, concise news/event context, compact provider health, and symbol/command search. Keep diagnostics secondary.

## Symbol Workstation

Show context header, quote/change, price/volume chart, timeframe controls, equity fundamentals or crypto derivatives, news/events, related context, source/freshness/caveat, and useful data gaps.

## Failure Behavior

Unknown or unsupported symbols render a useful unavailable page with valid navigation. Runtime failures retain symbol context and use explicit cached, stale, unavailable, or error state.

## Visual Gate

All seven required screenshots must exist and be inspected. AAPL/BTCUSDT charts must be nonblank or explicitly unavailable. Metadata must not dominate the first screen.

## Implemented Result

- `/` and `/?view=home` open the product Market Home rather than the 20-contract gallery.
- Canonical `view=asset` URLs open AAPL Equity Intelligence or BTCUSDT Crypto Intelligence.
- Search, spotlight, market tape, and heatmap links preserve asset state.
- Unknown symbols stop at an explicit unavailable surface and never inherit AAPL/BTC fixture rows.
- Product mode defaults to `cache`; missing API configuration is visibly downgraded to `runtime-fallback`.
- Fixture mode remains deterministic and visibly labeled.
- Ten inspected screenshots cover normal desktop/tablet/mobile, runtime fallback, unknown symbol, and chart fallback.

Outputs are research calculations and information displays only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, broker actions, autonomous actions, or execution instructions.
