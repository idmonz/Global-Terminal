# Catalyst Graph System

`lib/catalyst_graph.py` builds graph-style relations between news events, regions, countries, assets, sectors, macro factors, commodities, crypto factors, and scenario evidence.

## Node Types

- `news_event`
- `region`
- `country`
- `asset`
- `sector`
- `macro_factor`
- `commodity`
- `crypto_factor`
- `scenario`

## Edge Types

- `mentions`
- `region_link`
- `asset_exposure`
- `sector_exposure`
- `macro_channel`
- `observed_move`
- `scenario_evidence`

The graph is represented as DataFrame node and edge lists. `lib/impact_visuals.py` can render a Sankey chart when valid nodes and edges exist.
