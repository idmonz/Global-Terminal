# WorldMonitor-Style War Room Upgrade

Goal 10B upgrades the War Room toward a map-first intelligence workflow while keeping all runtime code project-native.

## New Modules

- `lib/war_room_live_data_router.py`
- `lib/osint_map_layers.py`
- `lib/world_event_geocoder.py`
- `lib/live_news_event_pipeline.py`
- `lib/map_event_clusterer.py`
- `lib/map_marker_engine.py`
- `lib/geospatial_tooltip_engine.py`
- `lib/war_room_timeline_engine.py`

## Capabilities

- Layer registry for news, conflict/sanctions, energy, shipping, ports, historical AIS, AISStream, OpenSky, USGS, weather, NWS, NASA FIRMS, country risk, crypto/geopolitical events, and provider gaps.
- Event normalization, deduplication, inferred geocoding, clusters, hotspot cards, timeline rows, marker payloads, and source/freshness/confidence tables.
- Missing-key panel for AISStream, OpenSky, NASA FIRMS, and NWS-style optional providers.

No WorldMonitor source is copied, imported, or required.

## Goal 11 Update

Goal 11 adds a local Personal Research Operating System layer. It stores private workspace state in SQLite under `data/private/`, adds watchlist/alerts/reports/strategy decision-log workflows, links OSINT/provider context to watchlist records, and remains manual, research-only, and release-hygiene controlled. No external source code, external folders, private DBs, secrets, live trading, broker execution, or background automation are included in release artifacts.
