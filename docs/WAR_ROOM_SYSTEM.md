# War Room System

The War Room is implemented by `lib/war_room.py`, `lib/event_stream.py`, `lib/geo_layers.py`, `lib/intelligence_scoring.py`, `lib/country_risk_model.py`, and `pages/14_War_Room.py`.

## Page Shape

- Header command strip with UTC/local time, global risk state, AI provider availability, WorldMonitor adapter status, freshness summary, and command mode.
- Goal 7 workspace preset selector and provider health strip.
- Map-first main view with event markers, static chokepoints, route exposure proxies, severity legend, freshness legend, and layer controls.
- Right rail with event feed cards, AI brief context, strategic posture proxy, forecast/scenario watch, country risk ranking, chokepoint risk, market impact, crypto stress, source freshness, provider health, and data gaps.
- Bottom tabs for market radar, stress proxy, crypto/energy mini-panels, event timeline, and data gaps.

## Data Behavior

- Events follow the schema in `lib/event_stream.py`.
- Coordinates come from source fields when available.
- Missing coordinates can fall back to clearly marked country/region centroids.
- Chokepoints and route arcs are static/proxy layers.
- No live AIS, military flight, or private OSINT feed is claimed.
- Layer payloads keep unavailable layers visible with provider/source/freshness/caveat fields.

## Degradation

The page works without API keys. Optional feeds show as unavailable or estimated through source-status and layer-status tables.

## Goal 9 Macro / Energy / Chokepoint Rail

War Room state now includes macro, energy, chokepoint, and route exposure rail payloads. The default War Room payload is static/proxy-labeled to avoid heavy provider calls on page load.

Route exposure and shipping/chokepoint outputs do not claim live AIS.
# Goal 10 Update

War Room is now connected to the workspace router and drill-down card system. NOAA AccessAIS is labeled historical-only, AISStream remains unavailable without key/probe success, and no live AIS is claimed from proxy/static layers.

## Goal 10B Update

War Room now consumes `war_room_live_data_router`, `osint_map_layers`, `live_news_event_pipeline`, `world_event_geocoder`, `map_event_clusterer`, `map_marker_engine`, `geospatial_tooltip_engine`, and `war_room_timeline_engine` payloads.

The page exposes layer quality, missing-key reports, event clusters, markers, region risk heatmap metadata, and source/freshness/confidence labels.
