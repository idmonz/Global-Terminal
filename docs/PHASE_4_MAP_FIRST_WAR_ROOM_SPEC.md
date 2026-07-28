# Phase 4 Map-First War Room Spec

Updated: 2026-06-17

Phase 4 implements a clean-room map-first War Room contract and workstation view for the Global Macro + Equity + Crypto + Commodity + Geopolitical Risk Terminal.

The slice turns existing War Room events, provider health, layer runtime, news-derived rows, and Phase 2F event-to-asset graph context into source/status-aware map markers, provider-gated layers, timeline filters, compare-window readiness, and explicit unavailable capability boundaries. It does not add broker execution, order routing, auth, billing, hosted persistence, graph databases, paid provider dependencies, user accounts, live AIS, live flight tracking, or live sanctions markers.

## Delivered Surface

- Python contract builder: `lib/war_room_map.py`
- API envelope builder: `build_api_war_room_map_payload()`
- Optional backend getter/route: `get_war_room_map_payload()` and `GET /api/war-room-map`
- Static fixture: `static/api-fixtures/war-room-map.json`
- Web workstation view: `/?view=war-room-map`
- Focused tests: `tests/test_war_room_map_contracts.py`
- Web fixture validator coverage: `apps/web/scripts/validate-fixtures.mjs`

The payload remains additive under `API_CONTRACT_VERSION = "phase_2b.v1"` with payload type `war_room_map`.

## Contract Shape

The map payload data object contains:

- `war_room_map_version`: currently `war_room_map.v1`
- `markers`: source-backed, fixture, approximate, or static/proxy event marker records
- `layers`: source-status-aware layer runtime records
- `timeline_filters`: deterministic local time-window filter rows
- `compare_windows`: schema-ready compare options with saved persistence unavailable
- `provider_requirements`: layer/capability provider gating matrix
- `readiness`: unavailable live/provider/persistence/execution capability boundary
- `evidence_refs`: external/prior-phase evidence cards used as behavior references
- `summary`: marker, coordinate, layer, live-claim, persistence, and compliance counts

Marker records include:

- `marker_id`
- `event_id`
- `title`
- `summary`
- `lat`
- `lon`
- `coordinate_method`
- `coordinate_status`
- `source_status`
- `availability`
- `provider`
- `source`
- `source_url`
- `fetched_at`
- `confidence`
- `severity`
- `severity_score`
- `region`
- `domain`
- `layer_ids`
- `related_asset_node_ids`
- `event_graph_node_id`
- `timestamp`
- `caveat`
- `data_gap`
- `not_financial_advice`

Layer records include:

- `layer_id`
- `label`
- `domain`
- `provider`
- `source`
- `source_status`
- `availability`
- `row_count`
- `requires_key`
- `freshness`
- `latest_fetched_at`
- `caveat`
- `data_gap`
- `recommended_action`

## Source And Coordinate Policy

Markers are emitted only when a safe coordinate exists. Coordinate labels are explicit:

- `source-backed`: source/provider coordinates are present.
- `fixture`: deterministic fixture coordinates for web-shell development.
- `static/proxy`: static registry or proxy rows such as chokepoints.
- `approximate`: named-location, regional-centroid, or country-centroid placement.
- `unavailable`: no safe coordinate; not rendered as a map marker.

Every non-source coordinate adds an explanatory `data_gap`. Static chokepoints remain proxy context and never claim live AIS or vessel-flow coverage.

## Provider Gating

Live map claims require fresh or cached provider evidence. In deterministic fixture mode:

- Public fixture/news and static chokepoint markers render as fixture or proxy/static.
- Layer rows with no live runtime evidence remain `unavailable`, `missing-key`, or `proxy/static`.
- OpenSky flight tracking remains `missing-key`/unavailable unless credentials and state-vector fetches are verified.
- AIS and sanctions marker capabilities remain unavailable.
- Market reaction layers are context/proxy unless provider-backed market data is fresh or cached.

The `provider_requirements` matrix carries layer status, provider status, key requirements, row counts, recommended actions, and `live_claim_allowed`.

## Timeline And Compare Policy

Timeline filters are local deterministic controls:

- `6h`
- `24h`
- `7d`
- `30d`
- `all`

Compare windows are schema-ready only:

- `previous_24h`
- `previous_7d`
- `saved_compare_session`

Saved compare sessions are unavailable because hosted persistence, auth, billing, and user accounts are not part of Phase 4.

## Evidence And License Boundary

Phase 4 reused Phase 2E/2F/3 evidence instead of copying external code.

Evidence refs included in the payload:

- WorldMonitor: map/layer/provider-health behavior only; AGPL source is not copied.
- worldview: timeline and compare-window behavior only; NASA-license source/assets are not copied.
- osiris: OSINT provider-gating behavior only; no source is vendored.
- OpenBB: provider-contract hierarchy behavior only; AGPL source is not copied.
- BB-Terminal/Bloomberg-style references: dense workstation behavior only; direct copying remains blocked.
- Phase 2F Event-To-Asset Graph: first-party graph context for related node IDs.

No external project source, visual asset, AGPL source, NASA source, or missing-license source is copied.

## Web Workstation View

The Next.js shell adds `war-room-map` to fixture definitions.

The view renders:

- Map-first command/status strip
- Schematic map stage computed from marker lat/lon
- Coordinate legend for source, approximate, static/proxy, and unavailable states
- Marker inspector with source URL, fetched timestamp, confidence, graph nodes, caveat, and data gap
- Layer gate stack with source-status pills
- Timeline filter controls
- Compare-window readiness cards
- Provider gate matrix
- Unavailable capability boundary
- Existing caveat/source rail

No Mapbox, MapLibre, deck.gl, broker workflow, auth, billing, persistence, or paid provider dependency is added.

## Verification

Implemented test and build coverage:

- `python -m pytest tests/test_war_room_map_contracts.py -q`
- `python -m pytest tests/test_war_room_map_contracts.py tests/test_command_workspace_contracts.py tests/test_event_asset_graph_contracts.py tests/test_api_fixture_export.py tests/test_api_backend_routes.py tests/test_api_contracts.py -q`
- `python scripts/export_api_fixtures.py`
- `python -m py_compile app.py lib/api_contracts.py lib/event_asset_graph.py lib/command_workspace.py lib/war_room.py lib/layer_registry.py lib/war_room_map.py backend/api/app.py scripts/export_api_fixtures.py`
- `npm --prefix apps/web test`
- `npm --prefix apps/web run lint`
- `npm --prefix apps/web run build`

Visual verification:

- In-app Browser was unavailable in this session.
- Local Playwright was not installed.
- HTTP render-marker checks passed for `http://127.0.0.1:3000/?view=war-room-map`.
- Headless Edge screenshots were captured for desktop and narrow/mobile layouts:
  - `review_workspace/phase4_visual/war-room-map-desktop.png`
  - `review_workspace/phase4_visual/war-room-map-mobile-tall.png`
- Desktop and narrow captures showed visible unavailable/proxy states, readable marker inspector, usable layer gates, and no obvious UI overlap after mobile CSS tightening.

## Remaining Gaps

- The map stage is a schematic fixture-driven surface, not a MapLibre/deck.gl production map.
- Live AIS, live flight tracking, live sanctions markers, and vessel-flow telemetry remain unavailable.
- Compare windows are local schema rows only; saved compare sessions require a later persistence/auth slice.
- Market impact links remain contextual and non-advisory.
- A richer daily brief and research-memory workflow belongs to Phase 5.
