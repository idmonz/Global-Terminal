# News Market Impact Engine

The News to Market Impact Engine is implemented by `lib/news_asset_linker.py`, `lib/market_impact_engine.py`, `lib/impact_visuals.py`, and updates to `pages/6_News.py`.

## Pipeline

1. Extract entities and keywords from news/events.
2. Classify event domain and market channel.
3. Map entities, regions, and keywords to related assets.
4. Optionally compute recent asset reactions from real price data.
5. Build impact tables, cards, charts, and scenario evidence rows.

## Goal 7 UI Deepening

- News Intelligence now includes a top event ticker strip, provider health strip, source freshness visuals, market-impact cards, catalyst graph, geopolitical maps, chokepoint route proxies, and AI context with data gaps.
- Live/polling status is explicit. RSS/GDELT polling remains controlled by the existing page flow or provider tests; no background feed starts on launch.

## Language

Allowed labels include:

- Observed related market move
- Potential channel
- Proxy reaction
- Correlation context
- Data gap

The engine does not claim that a news item caused a market move.

## Goal 9 Energy / Chokepoint Evidence

`lib/energy_market_impact.py` and `lib/shipping_chokepoint_engine.py` add energy and chokepoint evidence payloads for Scenario Lab and War Room.

Accepted language is proxy reaction, potential channel, and observed related move. No causality is claimed.
