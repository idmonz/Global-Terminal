# Phase 5H API And Data Contract

Updated: 2026-06-20

## Existing Boundary

Phase 5H extends the existing `phase_2b.v1` `war_room_map` and `map_news_event_fusion` payloads. It does not create another broad envelope.

## Marker Requirements

Every rendered marker carries:

- stable `marker_id` and `event_id`;
- title, summary, domain, region, severity;
- latitude/longitude;
- `coordinate_method` and `coordinate_status`;
- provider, source, `source_url`;
- `fetched_at`, `freshness`, `source_status`, availability;
- confidence, caveat, data gap;
- layer IDs and evidence-backed related asset node IDs;
- `not_financial_advice=true`.

Provider-native methods such as `usgs_geojson` and `opensky_state_vector` are source-backed coordinates. Country/region centroids are approximate. Static registries are static/proxy.

## Layer Requirements

Each layer preserves source `row_count` and adds `visible_marker_count`. The latter must equal the markers in the returned payload that reference that layer. Availability requires successful provider evidence, not merely a configured environment variable.

## Runtime Inputs

- `include_runtime`: fetch free-first runtime feeds.
- `.env`: loaded server-side; only configuration booleans/status reach product contracts.
- Optional OpenSky: attempted only when credentials are configured; 401/error returns no markers.
- USGS/RSS/GDELT: cache, stale fallback, timeout, and provider provenance remain in existing runtime cache paths.

## Fusion Requirements

The fusion payload adds source-bound `news_rows` for client-side event matching. Fallback news is visibly labeled as fallback rather than presented as a semantic match. Connected assets remain absent unless event graph or explicit ticker evidence exists.

## Determinism

Fixture export remains network-free, fixed, secret-safe, and explicitly fixture/proxy. Runtime rows are never written into static fixtures.
