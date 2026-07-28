# Heatmap Visualization System

Goal 10B adds an internal heatmap engine inspired by modern market heatmap usability, implemented entirely in project-native Python payloads and Streamlit/Plotly-ready tables.

## Modules

- `lib/heatmap_tile_engine.py`: tile sizing, coloring, grouping, labels, metadata, and treemap rows.
- `lib/heatmap_color_scales.py`: change, risk, provider health, data quality, volatility, and event severity buckets.
- `lib/heatmap_tooltip_engine.py`: equity, crypto, portfolio, provider, War Room, and Energy tooltips.
- `lib/heatmap_drilldown_engine.py`: route and command suggestions for assets, sectors, crypto, providers, portfolios, regions, and energy items.
- `lib/heatmap_visual_theme.py`: dark-friendly theme and legends.
- `lib/heatmap_layout_engine.py`: layout payloads for market, provider, source freshness, portfolio, factor, War Room, and Energy heatmaps.
- `lib/market_overview_layout.py`: overview-ready market board with summary, heatmaps, timeline, RMI, volatility, and click-next cards.

## Supported Modes

- Size: market cap, equal fallback, volume, dollar volume, portfolio weight, risk contribution, open interest, TVL, provider coverage, event count, risk score.
- Color: daily/weekly/monthly change, volatility, volume z-score, drawdown, relative strength, liquidity stress, funding, OI change, liquidation pressure, data quality, provider health, source freshness, macro sensitivity, War Room risk, Energy risk.
- Group: sector, industry, asset class, country, region, exchange, portfolio bucket, provider domain, watchlist group, crypto sector, event type, chokepoint.

Missing market cap falls back to equal sizing and adds a tooltip data-gap label.
