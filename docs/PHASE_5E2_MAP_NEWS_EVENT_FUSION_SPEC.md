# Phase 5E.2 Map-News-Event Fusion Spec

Updated: 2026-06-19

This checkpoint turns the War Map from an isolated map panel into a source-bound intelligence workspace. It is still not the final commercial terminal, but it now connects map markers, related news, event graph links, provider/layer truth, and market heatmap context in one web surface.

## User Problem Addressed

The user correctly reported that the web app looked polished but did not yet behave like WorldMonitor, NASA Worldview, TradingView, Finviz, or a Bloomberg-like terminal. The previous slices added contracts, a web shell, Leaflet, chart rendering, and a market heatmap, but the map, news, events, and market context were still mostly isolated.

This slice specifically addresses:

- WorldMonitor-style map plus news/source/provider context.
- Worldview-style map interaction, layer gates, timeline/compare readiness.
- TradingView/Finviz-style heatmap reaction context.
- Bloomberg-like command/workstation density while keeping source truth visible.

## Implemented Contract

New reusable module:

- `lib/map_news_event_fusion.py`

New API envelope builder:

- `build_api_map_news_event_fusion_payload()` in `lib/api_contracts.py`

New optional backend route:

- `GET /api/map-news-event-fusion`

New deterministic fixture:

- `static/api-fixtures/map-news-event-fusion.json`

Payload type:

- `map_news_event_fusion`

Contract version:

- `phase_2b.v1`

Contract fields:

- `markers`
- `selected_marker`
- `related_news`
- `event_links`
- `connected_assets`
- `heatmap_context`
- `layer_health`
- `provider_health`
- `timeline_windows`
- `unavailable_sources`
- `source_register`
- `readiness`
- `evidence_refs`
- `summary`

Every source-bearing row keeps provider/source status, freshness when available, fetched timestamp when available, confidence, caveat, data gap, and non-advisory markers. Coordinates remain labeled by method/status on marker rows.

## Web Surface

New web view:

- `/?view=map-news-event-fusion&mode=fixture`

The view includes:

- Runtime/source boundary banner.
- Summary tiles for markers, event links, connected assets, heatmap context, layers, and advisory boundary.
- Leaflet map with marker inspector, timeline controls, layer gates, and map-linked events.
- Selected-event card.
- Related-news stack.
- Heatmap reaction context.
- Event-to-asset links.
- Connected assets.
- Provider/layer truth panel.
- Source register.

Market Intelligence mobile heatmap layout was also tightened so the Finviz/TradingView-style tiles remain readable on narrow screens.

## Source Truth

Current fixture truth:

- `map_news_event_fusion` is source-bound but mostly fixture/proxy/static.
- It does not claim live AIS, flight tracking, sanctions, broker execution, auth, billing, hosted persistence, or paid-provider coverage.
- Heatmap context remains synthetic fixture data until provider-backed constituents, market caps, returns, and freshness are added.
- Live/cache rows appear only when upstream provider contracts contain such statuses.

Runtime safety:

- No external AGPL/NASA/missing-license source or visual asset was copied.
- Runtime code does not reference blocked external source tree names.
- No raw `.env`, bearer token, API key, private path, or local absolute path is exported in fixtures.
- No directional trading advice or execution path is introduced.

## Visual Verification

Browser connector was not available in this session, so verification used a local production Next.js server plus headless Chrome screenshots. Chrome on Windows required waiting for the screenshot file before stopping the server; otherwise it captured a connection-refused page.

Final screenshots:

- `dist/phase5e2-map-news-event-screenshots/map-news-event-fusion-desktop.png`
- `dist/phase5e2-map-news-event-screenshots/map-news-event-fusion-mobile.png`
- `dist/phase5e2-map-news-event-screenshots/market-intelligence-heatmap-desktop.png`
- `dist/phase5e2-map-news-event-screenshots/market-intelligence-heatmap-mobile.png`

HTTP markers verified:

- `Map News Event Fusion`
- `Heatmap Reaction Context`
- `leaflet-war-map`

## Verification

Passed:

- `python -m py_compile app.py lib/map_news_event_fusion.py lib/api_contracts.py backend/api/app.py scripts/export_api_fixtures.py`
- `python -m pytest tests/test_map_news_event_fusion_contracts.py -q`
- `python -m pytest tests/test_api_fixture_export.py tests/test_api_backend_routes.py tests/test_api_contracts.py -q`
- `python -m pytest tests/test_goal11_no_external_source_copy.py tests/test_goal11c_no_external_source_copy.py tests/test_goal11d_no_external_source_copy.py tests/test_goal12e_release_hygiene.py tests/test_visual_terminal_upgrade.py -q`
- `python -m pytest -q`
- `python scripts/export_api_fixtures.py`
- `npm.cmd --prefix apps/web test`
- `npm.cmd --prefix apps/web run lint`
- `npm.cmd --prefix apps/web run build`
- `npm.cmd --prefix apps/web run test:runtime-api` after running it separately from build
- `npm.cmd --prefix apps/web audit --audit-level=high`

Notes:

- Running `npm.cmd --prefix apps/web run test:runtime-api` in parallel with `next build` can intermittently fail on port `3031`; sequential rerun passed.
- Full pytest passed with the existing cointegration collinearity warnings only.

## Remaining Gaps

This is still not the final B2C product:

- Equity, financials, options, and crypto deep workspaces still need to migrate richer Streamlit functionality into web-native surfaces.
- Most fixture mode rows are not live market data.
- Market heatmap needs real provider-backed constituents, market caps, returns, and freshness.
- Related news matching is deterministic and conservative; it needs stronger entity extraction, geocoding, and provider-backed ranking.
- The map needs clustering, richer popups, compare mode, and live provider state once verified feeds exist.
- Daily brief, research memory, watchlists, alerts, accounts, billing, and persistence remain future phases.

## Next Recommended Slice

Phase 5E.3 should migrate the missing Streamlit intelligence tabs into web-native, source-bound workstations:

1. Equity Intelligence deep page.
2. Crypto Intelligence deep page.
3. Financial/Fundamentals page.
4. Options/Quant page with unavailable/provider-required states where live options data is missing.
5. Screener/heatmap drilldown from market tiles into symbols/sectors.

The goal is to stop the web app from feeling like a contract gallery and make it behave like a daily-use market terminal.
