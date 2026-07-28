# Phase 5Y Visual QA Report

Updated: 2026-07-01

## Method

The in-app browser was unavailable in this session. The repository
`playwright-core` package and local Chrome were used as the documented fallback.
Assertions were performed against the production Next.js build, not a static HTML
mock.

## Online Evidence

Directory:

`review_workspace/phase5y_map_intelligence_release_verified/`

Inspected captures:

- `war-map-online-desktop.png`
- `war-map-selected-context.png`
- `news-from-map.png`
- `aapl-map-origin.png`
- `war-map-online-mobile.png`
- `summary.json`

Final assertions:

- runtime online;
- Leaflet map ready;
- 37 markers and 29 source-backed markers;
- 24 loaded desktop tiles and 8 loaded mobile tiles;
- five priority event controls;
- selected event updates the inspector and URL without a provider reload;
- current map does not silently switch to replay;
- desktop map starts at 405px, below the 430px gate;
- mobile map starts at 600px, below the 720px gate;
- no horizontal overflow;
- no console or page errors;
- when direct event reporting is zero, the News desk action is visible;
- News route has 41 visible rows;
- AAPL chart is ready and has a return-to-selected-map-event action.

Manual review confirmed the selected USGS earthquake shows provider, source/freshness,
coordinate method, confidence, source action, explicit no-direct-reporting state,
bounded transmission paths and connected assets.

## Offline Evidence

Directory:

`review_workspace/phase5y_map_intelligence_offline_release_verified/`

The production web build was started with an intentionally invalid API base. This
did not stop or alter the real FastAPI process.

Final assertions:

- runtime offline and fallback notice visible;
- two deterministic fixture/proxy markers;
- zero source-backed markers;
- map ready with 15 desktop and 9 mobile tiles;
- selected fixture event and source-linked reporting remain inspectable;
- News fixture surface contains visible rows;
- AAPL fixture chart remains ready;
- return-to-map action remains present;
- no horizontal overflow;
- no console or page errors.

## Visual Comparison Findings

Adopted clean-room behavior:

- WorldMonitor: map-first event density, layer control and selected-event evidence;
- worldview: persistent map interaction and visible spatial context;
- OpenBB: source-aware panels and provider caveats;
- Bloomberg-like terminals: compact, scan-oriented information density;
- supplied War Room and WorldMonitor references: map/inspector balance and operations
  desk hierarchy.

Not copied:

- external source code;
- screenshots, imagery, icons, fonts, datasets or layout assets;
- proprietary branding or exact compositions.

## Remaining Visual Gaps

- Mobile first viewport still shows operational controls before the full map.
- Layer controls are honest but broad unavailable categories reduce signal density.
- The right inspector needs richer verified weather, flight, AIS and sanctions rows.
- The map is point/event oriented; polygon, route, weather raster and time animation
  depth remain below the cited benchmarks.
- Cold runtime latency is too high for a hosted daily-use terminal.

