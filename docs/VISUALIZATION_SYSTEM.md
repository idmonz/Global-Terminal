# Visualization System

## Goal 7 Visual Additions

- Portfolio Quant Lab adds dark Plotly equity curves, drawdowns, rolling risk, monthly heatmaps, allocation charts, correlation, attribution, turnover, and Monte Carlo fan charts.
- Data Provider Center adds capability and gap tables plus provider health/freshness surfaces.
- Terminal shell helpers add workspace presets, provider health strip, ticker tape, status console, right-rail panels, and layer-control payloads.

## Overview Terminal

`app.py` now composes:

- Cross-asset metric deck with daily return, 1M return, volatility regime, sparkline, and source badge.
- Selected asset chart modes.
- Market radar and signal convergence panels.
- Heatmap strip.
- Crypto intelligence mini-panel.
- Equity intelligence mini-panel.
- Energy/geopolitical mini-panel.
- Risk mini-panel.
- Event maps, chokepoint risk map, market region risk map, and source freshness table.
- AI situational brief.

## Map System

`lib/map_viz.py` builds:

- Event maps.
- Terminal event maps.
- Chokepoint maps and chokepoint risk maps.
- Country risk maps.
- Country news density maps.
- Energy route proxies.
- Market region maps.
- Event timeline charts.
- News severity bars.
- Source freshness charts.

No map claims live vessel flow unless an external AIS provider is added later. Static route and chokepoint maps are labeled as proxy estimates.

## Source Status

Panels carry `DataResult` source, freshness, warning, and estimate metadata where available.

## Visual Builder Modules

- `lib/terminal_ui.py`: reusable terminal headers, badges, metric strips, cards, mini bars, and sparklines.
- `lib/intelligence_cards.py`: market, crypto, energy, risk, news, AI, and data-gap cards.
- `lib/source_freshness.py`: freshness status, badge payloads, source tables, and warnings.
- `lib/market_radar.py`: normalized radar payloads and composite score.
- `lib/news_intelligence.py`: news normalization, impact matrix, timeline, regional cards, and dashboard payload.
## Goal 6 Visual Intelligence Additions

- War Room maps use `lib/geo_layers.py` for dark event maps, static chokepoint layers, route exposure proxy arcs, country instability choropleths, event density, crypto stress, and regional market stress layers.
- Financial Terminal charts use `lib/financial_charts.py` for reported financial statements, margins, cash flow, debt/cash, valuation/profitability ratios, availability heatmaps, and data-gap-safe segment/geography panels.
- News impact visuals use `lib/impact_visuals.py` for event-asset heatmaps, impact matrices, catalyst Sankey charts, timeline overlays, asset proxy reaction bars, and scenario evidence contribution charts.
- All new visual layers preserve caveats in figure titles, status rows, or panel captions when data is estimated, static, or missing.
