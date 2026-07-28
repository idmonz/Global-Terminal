# Phase 5A Product-Parity Intelligence Workstation Spec

Updated: 2026-06-17

Phase 5A is a corrective product slice after Phase 4. Phase 4 produced valid contracts and a coherent web shell, but the web app still did not expose enough of the existing Streamlit product value. Phase 5A delivered the first product-parity workstation slice on 2026-06-17.

## Pre-Implementation Reality

The current web app has useful structure:

- Next.js shell with a dense workstation frame.
- Static API fixtures and optional FastAPI route shape.
- War Room map contract.
- Event-to-asset graph contract.
- Command workspace contract.
- Provider health, feed, layer, news, asset-universe, and AI readiness fixtures.

But it is still missing the product surfaces users expect:

- Stock/equity intelligence from `pages/2_Stock_Analyzer.py`.
- Financial/fundamental analysis from `pages/15_Financial_Terminal.py`.
- Crypto derivatives and market intelligence from `pages/8_Crypto_Intelligence.py`.
- Options and quant diagnostics from `pages/24_Options_Quant_Model_Lab.py`.
- Portfolio quant, screeners, market pulse, richer news, and chart-heavy workflows.
- A map that behaves more like WorldMonitor/worldview/osiris rather than a schematic marker stage.
- TradingView/Koyfin-style charting density.
- Bloomberg/BB-Terminal-style command navigation that opens real analysis workspaces.

## Product Objective

Turn the web app into the first real B2C intelligence workstation slice.

A user opening `http://127.0.0.1:3000/` should be able to inspect:

- Market Intelligence
- War Map
- Equity Intelligence
- Crypto Intelligence
- Financial / Fundamentals
- Options / Quant readiness
- News
- Provider Health
- Event Graph
- Commands

Every panel must show provider, source status, freshness, caveat, and data gap. If the data is unavailable, missing-key, fixture, proxy/static, or stale, that state must be visible.

## Required Implementation Slices

### 1. Product Parity Inventory

Build a contract that compares Streamlit capabilities against web capabilities.

Suggested module:

- `lib/product_parity_inventory.py`

Payload should include:

- Streamlit pages
- reusable `lib/` engines
- current web workspaces
- missing web surfaces
- priority migration queue
- external reference map
- summary

### 2. Equity Intelligence

Build a JSON-safe equity/stock contract and web view using existing engines.

Inputs to review:

- `pages/2_Stock_Analyzer.py`
- `pages/15_Financial_Terminal.py`
- `lib/financial_terminal.py`
- `lib/financial_charts.py`
- `lib/equity_scenarios.py`
- `lib/options_flow.py`
- `lib/news_asset_linker.py`

Expected route/view:

- `/api/equity-intelligence`
- `static/api-fixtures/equity-intelligence.json`
- `/?view=equity-intelligence`

### 3. Crypto Intelligence

Build a JSON-safe crypto contract and web view using existing engines.

Inputs to review:

- `pages/8_Crypto_Intelligence.py`
- `lib/crypto_derivatives.py`
- `lib/crypto_prices.py`
- `lib/crypto_scenarios.py`
- `lib/market_radar.py`
- `lib/crypto_onchain.py`

Expected route/view:

- `/api/crypto-intelligence`
- `static/api-fixtures/crypto-intelligence.json`
- `/?view=crypto-intelligence`

### 4. Chart Specifications

Move chart intent across the API boundary as JSON-safe chart specs, not Plotly or Streamlit objects.

Each chart spec should carry:

- chart ID
- chart type
- title
- series
- axes or dimensions
- unit
- provider
- source status
- fetched timestamp
- caveat
- data gap

The web layer may render simple native SVG/HTML charts first. Any new dependency must be reviewed for official docs, license, bundle impact, and audit output.

### 5. War Map Interaction Upgrade

Improve the map from a schematic placeholder toward a real interactive risk surface:

- map-like world/stage rendering
- marker focus
- news/event list linked to marker selection
- layer toggles
- timeline filtering
- compare window controls
- source/caveat rail
- unavailable AIS/flight/sanctions matrix

No fake live tracking is allowed.

### 6. Terminal Workspace Routing

Commands should route to real workspaces:

- `AAPL FA` -> equity intelligence
- `AAPL DES` -> equity/company description context
- `AAPL OMON` -> options/gamma proxy or explicit provider gap
- `BTCUSDT CRYPTO` -> crypto intelligence
- `REDSEA MAP` -> War Map filtered to Red Sea context
- `NI` -> news/market intelligence

This remains read-only research routing. It is not broker execution.

## External Reference Policy

Use external projects as behavior evidence only unless license review allows direct use.

- WorldMonitor/OpenBB/OpenAlice/OpenStock: AGPL, behavior-only.
- worldview: NASA, behavior-only.
- BB-Terminal: unclear archive license, behavior-only.
- Bloomberg-terminal/Dexter: README-only MIT evidence, direct copying remains needs-review.
- FinanceDatabase: MIT schema/taxonomy reference; avoid copying large row datasets.
- osiris: MIT; direct adaptation possible with attribution, but native implementation is preferred.

## Acceptance Criteria

- `apps/web` visibly contains equity and crypto intelligence workspaces.
- The web app renders actual chart/graph surfaces from JSON-safe specs.
- The War Map has interaction beyond the Phase 4 schematic placeholder.
- The terminal command workspace routes into real analysis views.
- Product parity inventory honestly lists what is still missing.
- All new payloads pass `validate_api_payload`.
- No API fixture leaks secrets, `.env`, local private paths, DataFrames, Plotly figures, Streamlit objects, or raw datetimes.
- `npm --prefix apps/web test`, lint, build, and high-severity audit pass.
- Visual verification is performed on desktop and narrow/mobile widths.

## Deferred Until Later

- Daily Brief and research memory.
- Auth, billing, hosted persistence, user accounts.
- Broker execution and order routing.
- Paid provider entitlements.
- Live AIS, live flight tracking, live sanctions markers.
- Full TradingView-equivalent charting or Bloomberg-equivalent command execution claims.

## Delivery Report

Status: implemented on 2026-06-17.

Implemented modules and contracts:

- `lib/product_parity_inventory.py`
- `lib/chart_specs.py`
- `lib/market_intelligence.py`
- `lib/equity_intelligence.py`
- `lib/crypto_intelligence_contract.py`
- Additive `phase_2b.v1` API payload builders for product parity, market intelligence, equity intelligence, and crypto intelligence.
- Optional backend getters/routes for `/api/product-parity`, `/api/market-intelligence`, `/api/equity-intelligence`, and `/api/crypto-intelligence`.
- Deterministic fixtures under `static/api-fixtures/` for `product-parity.json`, `market-intelligence.json`, `equity-intelligence.json`, and `crypto-intelligence.json`.

Implemented web surfaces:

- Market Intelligence first screen with cross-asset tape, risk heat, macro context, source rail, and native chart specs.
- Equity Intelligence, Financials, and Options aliases backed by the same source-labeled equity contract.
- Crypto Intelligence with market overview, derivatives, funding/open-interest/taker/long-short context, scenario rows, liquidity pressure proxy, and charts.
- Product Parity inventory workspace showing migrated, partial, and missing Streamlit surfaces.
- Upgraded War Map view with map-first stage, marker inspector, linked marker list, layer toggles, timeline controls, compare readiness, and unavailable provider states.
- Command routing for `NI`, `MAP`, `FA`, `DES`, `OMON`, and `CRYPTO` into read-only workspaces while preserving provider-required/unavailable live status.

Verification:

- `python -m py_compile app.py lib/api_contracts.py lib/product_parity_inventory.py lib/chart_specs.py lib/market_intelligence.py lib/equity_intelligence.py lib/crypto_intelligence_contract.py lib/command_workspace.py lib/war_room_map.py backend/api/app.py scripts/export_api_fixtures.py`
- `python -m pytest tests/test_product_parity_inventory.py tests/test_market_intelligence_contracts.py tests/test_equity_intelligence_contracts.py tests/test_crypto_intelligence_contracts.py tests/test_war_room_map_contracts.py tests/test_command_workspace_contracts.py tests/test_api_fixture_export.py tests/test_api_backend_routes.py tests/test_api_contracts.py -q`
- `python scripts/export_api_fixtures.py`
- `npm --prefix apps/web test`
- `npm --prefix apps/web run lint`
- `npm --prefix apps/web run build`
- `npm --prefix apps/web audit --audit-level=high`

Visual verification:

- The in-app browser surface was unavailable in this session.
- Chrome headless was used against a fresh production server at `http://127.0.0.1:3002`.
- Desktop screenshots were captured for market intelligence, equity intelligence, crypto intelligence, War Map, and product parity.
- Narrow/mobile screenshots were captured for market intelligence and War Map.
- Screenshot output: `dist/phase5a-screenshots/`.

Remaining gaps for Phase 5B:

- Dedicated screener workspace.
- Portfolio quant workspace.
- Full financial statement drilldowns.
- Full options book / volatility surface workflow.
- Optional live/cache runtime controls in the web UI.
- Production map renderer/data-source decision.
