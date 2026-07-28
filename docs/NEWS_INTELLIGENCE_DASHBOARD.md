# News Intelligence Dashboard

`lib/news_intelligence_dashboard.py` upgrades the News workflow with normalized event timelines, filters, map previews, impact cards, heatmaps, and source freshness.

## Capabilities

- Theme classification: energy, crypto, macro, geopolitics, weather, general.
- Asset linking for oil, energy equities, BTC/crypto, broad equities, and rates proxies.
- Region linking and map-preview rows for events with sufficient coordinate confidence.
- Duplicate handling through event id/title/source normalization.
- Source freshness table with confidence and truth labels.

Public news can be noisy, delayed, duplicated, or missing coordinates, so the dashboard keeps caveats visible.
