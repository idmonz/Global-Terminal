# Phase 2F Event-To-Asset Graph Spec

Updated: 2026-06-17

Phase 2F implements a clean-room event-to-asset graph contract for the Global Macro + Equity + Crypto + Commodity + Geopolitical Risk Terminal.

The graph links existing source-backed or proxy-labeled War Room/news/provider rows to regions, risk themes, sectors, commodities, FX pairs, crypto pairs, provider states, terminal commands, and the Phase 2E asset-universe reference schema. It does not add a graph database, hosted Supabase, auth, billing, paid provider dependency, or live graph persistence.

## Delivered Surface

- Python contract builder: `lib/event_asset_graph.py`
- API envelope builder: `build_api_event_asset_graph_payload()`
- Optional backend getter/route: `get_event_asset_graph_payload()` and `GET /api/event-asset-graph`
- Static fixture: `static/api-fixtures/event-asset-graph.json`
- Web workstation view: `/?view=event-graph`
- Focused tests: `tests/test_event_asset_graph_contracts.py`
- Web fixture validator coverage: `apps/web/scripts/validate-fixtures.mjs`

The payload remains additive under `API_CONTRACT_VERSION = "phase_2b.v1"` with payload type `event_asset_graph`.

## Contract Shape

The graph payload data object contains:

- `graph_contract_version`: currently `event_asset_graph.v1`
- `nodes`: JSON-safe node records
- `edges`: JSON-safe edge records
- `clusters`: grouped summaries by region, risk theme, and asset class where applicable
- `command_suggestions`: clean-room terminal actions routed from graph context
- `readiness`: persistence/live-store readiness and unavailable capabilities
- `evidence_refs`: external evidence cards used as behavior/product references
- `asset_universe_readiness`: Phase 2E asset-universe readiness summary
- `summary`: compact counts and truth-policy status

Node records include:

- `id`
- `type`
- `label`
- `source_status`
- `confidence`
- `provider`
- `source_url`
- `fetched_at`
- `caveat`
- `data_gap`
- `metadata`

Edge records include:

- `id`
- `source`
- `target`
- `relationship`
- `confidence`
- `source_status`
- `evidence`
- `caveat`
- `provider`
- `source_url`
- `fetched_at`

## Node Types

Phase 2F emits these first-party node types:

- `event`
- `region`
- `risk_theme`
- `sector`
- `commodity`
- `fx_pair`
- `crypto_pair`
- `provider`
- `asset_class`
- `command`

Phase 2E asset classes are imported as reference-schema nodes. Commodities are represented as a Phase 2F proxy asset-class gap because Phase 2E did not yet define a provider-backed commodity universe schema.

## Relationship Types

Phase 2F emits these relationship labels:

- `reported_by`
- `located_in`
- `mentions`
- `affects`
- `routes_to`
- `proxy_for`

Source-backed or event-field relationships keep the source row status where available. Rule-based market links use `source_status = "inferred/proxy"` with confidence and caveat.

## Rule Map V1

The first graph is deterministic and fixture-friendly.

Implemented rule groups:

- Red Sea, Bab el-Mandeb, Suez, Hormuz, shipping, tanker, chokepoint, vessel, freight:
  - Risk themes: energy chokepoint, global trade
  - Sectors: energy, shipping/logistics
  - Commodities: WTI crude, Brent crude
  - FX pairs: USD/JPY, EUR/USD
  - Crypto pair proxy: BTC/USD
  - Commands: `NI`, `MAP`, `FXC`, `WEI`, `GP`
- Crypto, bitcoin, BTC, ether, ETH, stablecoin, Binance, CoinGecko:
  - Crypto liquidity, digital assets, BTC/USD, ETH/USD
  - Commands: `NI`, `CRYPTO`, `GP`, `HP`
- Fed, rates, treasury, yield, inflation, dollar, DXY, currency, FX:
  - Macro rates, FX risk, financials, gold, USD/JPY, EUR/USD, BTC/USD
  - Commands: `NI`, `FXC`, `GP`, `HP`
- Earthquake, USGS, storm, wildfire, weather, natural:
  - Natural hazard, insurance, utilities, USD/JPY
  - Commands: `NI`, `MAP`

Related tickers supplied by event rows are mapped through a local clean-room ticker map for common fixture/runtime symbols such as `CL=F`, `BZ=F`, `BTC`, `ETH`, `DXY`, `SPX`, `NDX`, `XLE`, and `BDRY`.

## Evidence And License Boundary

Phase 2F reused the refreshed Phase 2E external audit evidence rather than re-running the full archive audit.

Evidence cards included in the payload:

- HelixDB: graph/query mental model only; mixed/needs-review evidence, no source copied.
- Supabase: future persistence/readiness architecture reference only; no hosted dependency added.
- WorldMonitor: provider truth/health behavior only; AGPL source not copied.
- OpenBB: optional provider/API route mental model only; AGPL source not copied or vendored.
- FinanceDatabase: MIT schema/taxonomy evidence already adopted in Phase 2E; CSV rows are not copied.
- BB-Terminal: command-workstation behavior recreated clean-room; direct copying remains blocked.

No external project is vendored. No AGPL/NASA/missing-license source is copied.

## Persistence Policy

Live graph persistence is explicitly unavailable in Phase 2F.

The `readiness` object marks these unavailable:

- `live_graph_persistence`
- `user_specific_watchlist_graph_state`
- `live_store`

Provider requirements before enabling persistence:

- A reviewed provider-backed graph or relational store.
- Source-level provenance and freshness metadata for every persisted row.
- Retention, auth, and privacy review before user-specific graph state.

No graph database dependency, hosted Supabase dependency, auth, billing, or accounts are added in this slice.

## Web Workstation View

The Next.js workstation adds `event-graph` to fixture definitions.

The view renders:

- Compact graph summary
- Unavailable persistence strip
- Relationship matrix
- Source-backed versus inferred/proxy edge counts
- Node tape
- Command suggestions
- Existing caveat/source rail

The implementation follows the current App Router server-rendered fixture pattern and uses the `searchParams` page prop plus `Link` navigation, matching the existing web shell and current Next.js documentation.

## Verification

Implemented test and build coverage:

- `python -m pytest tests/test_event_asset_graph_contracts.py -q`
- `python -m pytest tests/test_event_asset_graph_contracts.py tests/test_asset_universe_contracts.py tests/test_api_fixture_export.py tests/test_api_backend_routes.py tests/test_api_contracts.py -q`
- `python -m py_compile app.py lib/api_contracts.py lib/api_contract_panels.py lib/asset_universe.py lib/event_asset_graph.py backend/api/app.py scripts/export_api_fixtures.py`
- `npm --prefix apps/web test`
- `npm --prefix apps/web run lint`
- `npm --prefix apps/web run build`

Visual/browser verification is required for final acceptance reporting whenever local browser tooling is available.

## Remaining Gaps

- Commodity universe rows are proxy/classification nodes only; provider-backed commodity reference schema remains future work.
- Market impact links are rule-based context, not trade signals or investment advice.
- Live graph persistence and user-specific graph state remain unavailable.
- FastAPI remains optional/off by default.
- Broader command execution belongs to the next command workspace slice.
