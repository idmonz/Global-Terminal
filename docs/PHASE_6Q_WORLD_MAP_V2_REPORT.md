# Phase 6Q World Map V2 Report

Updated: 2026-07-30
Status: verified product-depth continuation; Phase 6Q hosted scheduler remains active and unverified

## Outcome

The commercial Next.js War Map now consumes the complete bounded runtime event
surface instead of the prior 100-row API truncation. A live production capture
observed 283 map events: 175 NASA EONET events, 100 USGS earthquakes, and 8
explicitly static/proxy chokepoints. At global zoom, Supercluster reduced those
283 events to 53 rendered markers; the Asia preset rendered 76. Counts are
time-dependent and are evidence from one run, not hard-coded product claims.

The slice adds:

- keyless NASA EONET GeoJSON fetching through the existing TTL, stale-fallback,
  timeout, and single-flight runtime cache;
- Point and LineString normalization with EONET and upstream-source provenance;
- provider-specific fire, storm, flood, volcano, sea/lake ice, earthquake, and
  other-natural-event layers;
- clean source/static coordinate labels and coordinate-derived broad regions;
- zoom-adaptive clustering with expansion zoom;
- Global, Americas, Europe, MENA, Asia, Pacific, and Fit events controls;
- shareable `mapRegion`, `lat`, `lon`, and `zoom` URL state;
- OSM tile health tracking and an automatic accessible fallback after bounded
  tile failures;
- a mobile layer drawer that is available but collapsed by default so it does
  not cover the primary map.

## Benchmark Evidence

The implementation is clean-room behavior adoption. No WorldMonitor, Worldview,
OpenBB, or supplied screenshot source or visual asset was copied.

- [NASA Worldview](https://worldview.earthdata.nasa.gov/) and its
  [April 2025 webinar](https://earthdata.nasa.gov/s3fs-public/2025-04/NASA%20Worldview%20Webinar%20April%202025.pdf)
  informed layer, event, timeline, compare, share, and snapshot expectations.
- [World Monitor features](https://www.worldmonitor.app/docs/features) and
  [map engine](https://www.worldmonitor.app/docs/map-engine) informed regional
  presets, progressive disclosure, adaptive clustering, and map/news/layer
  co-presence.
- [NASA EONET v3](https://eonet.gsfc.nasa.gov/docs/v3) is the implemented
  public event source. NASA's [data use policy](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy)
  remains linked for downstream reuse review.
- [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs) and its
  [cluster example](https://maplibre.org/maplibre-gl-js/docs/examples/create-and-style-clusters/)
  remain the preferred later vector-map path, not a dependency added in this
  slice.
- The [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/)
  makes clear that the public standard tile service is best effort, requires
  attribution, forbids bulk prefetch, and has no commercial SLA. The current
  product therefore exposes tile degradation and fallback rather than claiming
  an operational basemap guarantee.

## Visual Proof

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_phase6q_world_map_v2_visual.ps1
```

The independent verifier accepted five screenshots under
`review_workspace/phase6q_world_map_v2_visual/`:

- live desktop global map;
- live Asia preset;
- 390x844 live mobile viewport;
- full-height mobile journey;
- intentionally failed OSM tile request with accessible fallback.

The passing summary records 283 events, 275 source-backed coordinates, 53
global clusters, 20 loaded desktop tiles, 8 loaded mobile tiles, seven region
controls, zero horizontal overflow, zero duplicate IDs, zero unlabeled
controls, and no unexpected errors on live desktop/mobile. The deliberate tile
failure records expected failed tile requests and proves fallback rather than
hiding them.

All five captures were directly inspected. The empty EONET region leak was
fixed from `nan` to a transparent coordinate-derived broad region. The mobile
layer list was changed from a map-covering overlay to a collapsed drawer.

## Honest Remaining Gaps

This is a strong internal beta map, not Worldview or WorldMonitor parity.

- no satellite/raster science layer catalog, temporal animation, swipe/compare,
  charted layer values, globe projection, or snapshot export;
- no verified live AIS, flight, sanctions, conflict, outage, or authoritative
  weather-alert breadth;
- no production vector-tile provider, self-hosted tiles, offline region packs,
  CDN, tile SLO, or attribution-monitoring service;
- event-to-news matching remains sparse for many EONET rows;
- hosted map history/background refresh remains unverified;
- the public repository and unprotected `main` branch remain security/release
  decisions for the owner; no visibility or permission setting was changed by
  this slice.

The benchmark score stays 4/5. The next map slice should add a provider-neutral
basemap adapter, temporal playback over captured observations, layer search and
grouping, and one more verified live geopolitical layer before considering a
MapLibre migration.
