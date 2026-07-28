# Phase 5H Product Contract

Updated: 2026-06-20

## Canonical Journey

`Market Home -> Global Risk Map -> select event -> inspect news/source/asset context -> change layers/timeline/compare -> refresh -> return Home or supported asset`.

Canonical query state:

```text
/?view=war-room-map&mode=cache&layers=earthquakes,conflicts&timeline=24h&compare=off&event=<marker-id>
```

## First Viewport

The first viewport contains:

- product navigation, not the 20-contract gallery;
- a large interactive Leaflet world map;
- compact live/cache/fixture/proxy/unavailable counts;
- layer toggles and timeline/compare controls;
- selected-event inspector with provider, URL, fetched time, freshness, confidence, coordinate method, caveat, and data gap;
- related news and supported asset links only when evidence exists.

## Interaction Contract

- Marker click, event list click, layer toggle, timeline change, and compare change update URL state.
- Reload/back/forward restores URL-backed state.
- Keyboard users can operate toggles and event rows.
- Dense marker collections are rendered with first-party spatial bucketing/cluster counts; no external map code is copied.
- `data-map-state`, `data-map-marker-count`, and `data-map-layer-count` expose renderer evidence.

## Failure Contract

- `mapMode=fallback` renders an explicit diagnostic fallback, not a blank map.
- No coordinates yields an explicit empty map state.
- Provider failure remains cached, stale, rate-limited, missing-key, unavailable, forbidden, or error-labeled.
- Configured OpenSky credentials do not enable flight markers unless OAuth and `/states/all` succeed.
- Static chokepoints remain static/proxy and inferred coordinates remain approximate.

## Acceptance

Phase 5H passes only when keyless runtime USGS/news rows produce source-backed/inferred markers, fixture and fallback remain honest, URL state survives refresh, normal maps are nonblank at desktop/tablet/mobile, and full Python/web/release gates pass.
