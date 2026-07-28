# WorldMonitor Integration Guide

WorldMonitor is used as an optional design and adapter reference for geopolitical, route, chokepoint, event-map, and source-freshness panels.

## Boundary

- WorldMonitor is not a required runtime dependency.
- `external/worldmonitor-main/` is reference-only and ignored by `.gitignore`.
- This project does not copy AGPL code into runtime modules.
- Runtime Python files do not import from `external/`.
- This project does not scrape private or pro-gated surfaces.
- Adapter calls require `WORLD_MONITOR_BASE_URL` and optionally `WORLD_MONITOR_KEY`.
- 401, 403, timeout, and unavailable endpoint paths return `DataResult` warnings.
- Goal 7 Provider Center reports WorldMonitor adapter status as optional and does not import `external/`.
- Goal 7 terminal UX uses WorldMonitor-style concepts only: layer-first maps, right rail panels, freshness badges, and source/data-gap warnings.

## Implemented Adapter Areas

- `check_worldmonitor_status()`
- `get_route_intelligence()`
- `get_public_panel_metadata()`
- `get_supply_chain_chokepoints()`
- `get_hormuz_tracker_if_accessible()`
- `get_energy_panel_if_accessible()`

## UI Usage

- Energy/Geopolitics has a WorldMonitor Adapter tab.
- News and overview pages use WorldMonitor-inspired maps, cards, badges, source freshness, impact matrices, and timelines.
- Static route and chokepoint proxies are labeled when live adapter data is unavailable.

## Reference Concepts Implemented Locally

- Command-center layout in `app.py`.
- News command feed in `pages/6_News.py`.
- Heuristic severity, region, asset-channel, and credibility tagging in `lib/news_intelligence.py`.
- Chokepoint and route proxy maps in `lib/map_viz.py`.
- Market radar in `lib/market_radar.py`.
- Signal fusion in `lib/signal_fusion.py`.
- Hotspot scoring in `lib/hotspot_scoring.py`.

These are conceptual equivalents implemented in Python/Streamlit. They do not copy WorldMonitor runtime code.
## Goal 6 Boundary Update

Goal 6 uses WorldMonitor only as a conceptual UI/data-workflow reference for map-first layout, layer registries, event panels, freshness badges, chokepoint workflow, and multi-source convergence.

- Runtime modules do not import from `external/worldmonitor`.
- `external/` remains ignored and excluded from release packaging.
- Optional API usage remains behind explicit configuration such as `WORLD_MONITOR_BASE_URL`.
- War Room OSINT layers show unavailable/optional status unless a real provider is configured.

See also `docs/WORLDMONITOR_REFERENCE_BOUNDARY.md` and `docs/WORLDMONITOR_CONCEPTUAL_REFERENCE.md`.
