# Map-First OSINT Pipeline

The Goal 10B OSINT pipeline converts source-labeled public/official/proxy rows into map-friendly payloads.

## Flow

1. Normalize news/events with `live_news_event_pipeline`.
2. Geocode exact coordinates when present or infer region-level centroids with low-confidence labels.
3. Build OSINT layer metadata with source, key requirement, live/proxy/historical-only state, freshness, confidence, marker style, and caveat.
4. Cluster events by region/proximity.
5. Build marker payloads and geospatial tooltips.
6. Route the payload into War Room, Energy, and News pages.

## Truthfulness Rules

- NOAA AccessAIS is historical-only.
- AISStream is live only after key and successful probe.
- OpenSky is live/limited only after valid credentials or an allowed anonymous probe.
- NASA FIRMS is missing-key unless a MAP_KEY is configured.
- Inferred news locations are labeled as inferred or low-confidence.

## Goal 11 Update

Goal 11 adds a local Personal Research Operating System layer. It stores private workspace state in SQLite under `data/private/`, adds watchlist/alerts/reports/strategy decision-log workflows, links OSINT/provider context to watchlist records, and remains manual, research-only, and release-hygiene controlled. No external source code, external folders, private DBs, secrets, live trading, broker execution, or background automation are included in release artifacts.
