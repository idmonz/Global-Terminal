# News Intelligence System

## Modules

- `lib/news_intelligence.py`
- `lib/geopolitical_news.py`
- `lib/map_viz.py`
- `pages/6_News.py`

## Page Tabs

- Command Feed
- Market Impact
- Geopolitical Map
- Oil / Chokepoints
- Crypto / Risk
- Source Freshness
- AI Brief
- WorldMonitor Adapter

## Builders

`lib/news_intelligence.py` provides:

- `normalize_news_item()`
- `classify_news_asset_tags()`
- `classify_news_region()`
- `classify_news_severity()`
- `classify_news_credibility()`
- `extract_related_assets()`
- `build_news_timeline()`
- `build_market_impact_matrix()`
- `build_high_severity_feed()`
- `build_regional_news_cards()`
- `build_source_freshness_panel()`
- `build_worldmonitor_style_news_dashboard()`

## Classification

Classification is deterministic and heuristic. It uses keyword rules for:

- Asset channels: equity, rates, FX, crypto, oil, shipping, geopolitical, macro.
- Regions: Middle East, Red Sea, Europe, Russia / Ukraine, Asia, Americas, Global.
- Severity: critical, high, medium, watch.
- Credibility: official, major wire/media, secondary, unknown.

## Caveats

- Public news feeds may be delayed, duplicated, rate-limited, or missing coordinates.
- Coordinate maps only render rows with latitude and longitude.
- Regional and country-density cards are heuristic fallback views.
- AI briefs are button-triggered and use source freshness plus data gaps as prompt context.
