# Phase 5B Product System Design

Updated: 2026-06-18

Phase 5B is the corrective design checkpoint after Phase 5A. It exists because the current web app has a polished workstation frame, but it still does not behave like a daily-use commercial intelligence terminal.

## 1. Current-State Diagnosis

Current active project root in this session:

- `<local project root>/Global Terminal`

Repository caveat:

- This active folder currently has `.gitignore` but no `.git` directory. Future work should not claim a clean git status unless the git-backed copy is restored or reopened.

What works now:

- Streamlit remains the internal lab and contains richer workflows than the web app.
- `lib/` contains reusable engines for market data, financials, screeners, portfolio quant, options, reports, watchlists, War Room, OSINT, provider health, and runtime cache.
- API-ready `phase_2b.v1` envelopes exist.
- `static/api-fixtures/` has 15 validated fixtures.
- `apps/web` builds and renders a dense workstation shell.
- Focused verification passed on 2026-06-18:
  - `python -m pytest tests/test_product_parity_inventory.py tests/test_market_intelligence_contracts.py tests/test_equity_intelligence_contracts.py tests/test_crypto_intelligence_contracts.py -q -p no:cacheprovider`
  - `npm.cmd --prefix apps/web test`

What is not product-grade yet:

- Most web views are still fixture-first and contract-preview-like.
- Equity and crypto chart data in fixtures is labeled `provider: fixture` / `source_status: fixture`; this is not real daily analysis.
- Financials and options are aliases over the equity payload, not dedicated deep workspaces.
- Dedicated screener and portfolio quant workspaces are still missing in the web product.
- The current map is first-party SVG/proxy rendering, not a real geographic map engine with pan, zoom, tile attribution, layers, clusters, popups, and time navigation.
- The chart renderer is a minimal native SVG renderer, not a TradingView/Koyfin-like charting surface.
- The terminal command bar routes to views, but does not yet feel like a Bloomberg/BB-Terminal-style command workflow over real workspaces.
- The external Gold Quant Regime report gives a useful report structure, but its trade/execution language must be converted into non-advisory research/report language before product adoption.
- Uploaded/reference images are not visible through this current session state; future visual work must inspect any provided image assets directly when available.

Conclusion:

Phases 1 through 5A built useful foundations, but the B2C web product is still in workstation-shell plus deterministic-fixture stage. The next implementation must connect existing `lib/` engines and free-first runtime providers to product-grade web workspaces, while choosing real map/chart technology deliberately.

## 2. Fixture And Runtime Truth Table

Observed from `static/api-fixtures/*.json` on 2026-06-18.

| Fixture | Payload | Observed source status | Product interpretation |
|---|---|---|---|
| `ai-providers.json` | `ai_provider_status` | `available`, `missing-key` | Gemini/free-first readiness exists, but provider values must stay masked. |
| `asset-universe.json` | `asset_universe` | `reference-schema` | Reference schema, not live universe rows. |
| `command-workspace.json` | `command_workspace` | `fixture`, `missing-key`, `provider-required`, `proxy/static` | Command routing exists, but many commands are previews or provider-gated. |
| `crypto-intelligence.json` | `crypto_intelligence` | `fixture`, `inferred/proxy` | Current web crypto surface is not yet true live derivatives intelligence by default. |
| `equity-intelligence.json` | `equity_intelligence` | `fixture`, `inferred/proxy`, `provider-required` | Equity surface is useful schema but not full live financial/options intelligence. |
| `event-asset-graph.json` | `event_asset_graph` | mixed fixture/proxy/provider-required states | Graph thinking exists, persistence and live graph remain unavailable. |
| `market-intelligence.json` | `market_intelligence` | `fixture`, `inferred/proxy` | Market page is a preview of the intended daily surface. |
| `product-parity.json` | `product_parity_inventory` | `local/source-backed` | Strongest truth artifact for what is missing. |
| `war-room-map.json` | `war_room_map` | `fixture`, `missing-key`, `proxy/static`, `unavailable` | Honest source labeling exists, but map rendering is not yet product-grade. |

Design implication:

- The app is not broken in the sense of invalid contracts.
- It is incomplete in the sense of commercial product value.
- Phase 5C must prioritize real/free-first runtime mode and product-grade rendering over more decorative contract cards.

## 3. Streamlit-To-Web Gap Audit

| Streamlit/lab source | Existing capability | Current web state | Required migration |
|---|---|---|---|
| `pages/2_Stock_Analyzer.py` | Terminal overview, price/technicals, financial overview, valuation/quality, options/gamma proxy, news/events, scenario | Partial via `equity-intelligence`; mostly fixture/proxy | Dedicated equity workspace with live/cache mode, real chart stack, statements, options status, event links. |
| `pages/8_Crypto_Intelligence.py` | Futures price/volume, OI, funding, taker ratio, long/short, derivatives radar, heatmap modes, scenarios | Partial via `crypto-intelligence`; fixture/proxy | Live/cache Binance/CoinGecko runtime wiring, multi-chart crypto cockpit, liquidity/derivatives source status. |
| `pages/13_Screener.py` | Cross-asset screeners, filters, heatmap, scatter, watchlist, neutral AI summary | Missing web payload/workspace | New `screener_workspace` contract and web view. |
| `pages/15_Financial_Terminal.py` | Statement charts, margins, valuation ratios, earnings, revenue segments, availability heatmap | Alias over equity payload | Dedicated `financial_statement_workspace` contract with table and chart specs. |
| `pages/16_Portfolio_Quant_Lab.py` | Editable portfolio, saved local portfolios, backtests, attribution, drawdown, rolling risk, factor profile, strategy research | Missing web payload/workspace | New `portfolio_quant_workspace` contract, local-only mode, no account/broker features. |
| `pages/24_Options_Quant_Model_Lab.py` | Calculator, Greeks/IV, payoff templates, option-chain CSV, vol surface, option book, diagnostics, reports | Alias over equity options readiness | New `options_quant_workspace` contract with provider-gated chain/surface/GEX research. |
| `pages/14_War_Room.py` | Map-first event view, source freshness, layer controls, country risk, chokepoints, market impact | Partial `war-room-map` contract and SVG view | Real map renderer decision and implementation. |
| `pages/6_News.py` | Command feed, market impact, geopolitical map, chokepoints, crypto/risk, source freshness, AI brief | Partial `news` fixture | Link news rows into map, graph, market, reports, and command flow. |

## 4. Reusable `lib/` Engine Inventory

These modules already exist and should be reused instead of reimplementing from scratch:

| Domain | Key modules | Migration note |
|---|---|---|
| Screeners | `lib/screeners.py`, `lib/openbb_screener_backend.py`, `lib/heatmap_layout_engine.py` | Build JSON-safe screener rows, filter state, heatmap specs, scatter specs, source status. |
| Portfolio quant | `lib/portfolio_quant_lab.py`, `lib/portfolio_backtester.py`, `lib/performance_attribution.py`, `lib/portfolio_visuals.py`, `lib/portfolio_factor_router.py` | Convert DataFrames/Plotly outputs to JSON-safe charts/tables. Keep local-only and no broker/account. |
| Financials | `lib/financial_terminal.py`, `lib/financial_charts.py`, `lib/openbb_data_mapper.py` | Expose statements, ratios, earnings, availability matrix, source gaps. |
| Options | `lib/options_flow.py`, `lib/options_chain_quality.py`, `lib/options_vol_surface.py`, `lib/options_surface_quality.py`, `lib/options_book_*`, `lib/options_report_*` | Provider-gated options research, no dealer-position claims without source evidence. |
| Crypto | `lib/crypto_derivatives.py`, `lib/crypto_prices.py`, `lib/crypto_scenarios.py`, `lib/market_radar.py`, `lib/crypto_onchain.py` | Add live/cache controls and chart cockpit. |
| Maps/OSINT | `lib/war_room_map.py`, `lib/map_viz.py`, `lib/map_marker_engine.py`, `lib/map_event_clusterer.py`, `lib/osint_map_layers.py`, `lib/world_event_geocoder.py` | Feed a real map renderer with source-status-preserving markers/layers. |
| Reports | `lib/report_generators.py`, `lib/report_markdown_templates.py`, `lib/report_context_builder.py`, `lib/report_source_snapshots.py`, `lib/research_report_sanitizer.py` | Build source-bound report generator; avoid trading instructions. |
| Watchlists/alerts | `lib/watchlist_*`, `lib/alert_*` | Later retention layer after contracts and local-only state are stable. |

## 5. External Evidence Adoption Matrix

Use external projects as evidence cards, not code dumps.

| External source | License stance | Useful behavior | Local clean-room target |
|---|---|---|---|
| `agent-skills-main.zip` | direct-use-allowed for method guidance | Spec-first, task breakdown, source-driven, UI engineering, API design, testing, quality, security | Development workflow and prompt design only. |
| `worldmonitor-main.zip` | AGPL boundary | Layer-first map/news/provider-health/source-status behavior | War Map, OSINT Feed, provider rails, data-gap labels. |
| `worldview-main.zip` | NASA license caution | Timeline, compare windows, layer and URL-state thinking | Map timeline/compare state and layer toggles. |
| `osiris-master.zip` | MIT behavior reference | OSINT map/provider routing and earthquake-style APIs | Provider-gated OSINT runtime. Prefer native implementation. |
| `OpenBB-develop.zip` | AGPL/optional package caution | Provider registry, command map, finance workflow hierarchy | Optional adapter/contract shape, not copied source. |
| `BB-Terminal-main.zip` | blocked/no usable license signal | Command bar and terminal function routing | Native command grammar and workspace state. |
| `bloomberg-terminal-main.zip` | needs review | Dense watchlist/workstation components | Concept-only until license text is confirmed. |
| `FinanceDatabase-main.zip` | MIT | Asset universe schemas for equities, ETFs, funds, FX, crypto, indices | Reference schema and routing metadata. Avoid row-copy by default. |
| `supabase-master.zip` | reference only for now | Admin/status/persistence UX concepts | Future persistence readiness, no hosted auth now. |
| `dexter-main.zip` | needs review | Financial research agent planning/self-check loop | Source-bound assistant workflow, Gemini/free-first. |
| `helix-db-main.zip` | review before direct use | Graph/vector memory concepts | Future event-asset memory design only. |
| `optlib-master.zip` | MIT-style option pricing reference, verify exact license | Options pricing formulas and chain behavior | Native options model verification or attribution-reviewed adaptation. |

## 6. Commercial Product Benchmarks

Current official/product references checked on 2026-06-18:

- OpenAI prompt guidance: `https://developers.openai.com/api/docs/guides/prompt-guidance`
- TradingView features: `https://www.tradingview.com/features/`
- Koyfin features: `https://www.koyfin.com/features/`
- Bloomberg Terminal: `https://professional.bloomberg.com/products/bloomberg-terminal/`
- Leaflet docs: `https://leafletjs.com/`
- MapLibre GL JS docs: `https://maplibre.org/maplibre-gl-js/docs/`

Benchmark takeaways:

- TradingView sets the charting/screener/workspace expectation: multiple chart panels, indicators, financial overlays, screeners, watchlists, alerts, and fast search/command behavior.
- Koyfin sets the reports/portfolio/financial-analysis expectation: portfolios, benchmarks, reports, financial analysis, screeners, market dashboards, and alerts.
- Bloomberg sets the integrated terminal expectation: data, news, research, charts, analytics, portfolio analytics, and command-style workflows in one solution.
- Leaflet is small and mobile-friendly for map basics; it is suitable if the product wants pragmatic map interactivity quickly.
- MapLibre offers richer WebGL vector maps, clusters, popups, realtime examples, heatmaps, time sliders, and advanced map controls; it is more powerful but heavier.

## 7. Product Information Architecture

The web app should stop behaving like a fixture viewer and become a workstation with these desk families:

| Workspace | User job | Primary contracts | Product panels | Unavailable state |
|---|---|---|---|---|
| Today / Daily Brief | Answer what changed since last open | news, market, war map, graph, provider health, reports | Executive brief, change list, source gaps, next commands | AI unavailable -> rule-based brief. |
| Market Intelligence | Cross-asset pulse | market, feeds, provider health, chart specs | Tape, heatmap, rates/FX/commodity/crypto panels, chart wall | Fixture/proxy rows labeled. |
| War Map / World Monitor | Inspect event geography | war-room-map, layers, news, graph | Real map, markers, layers, timeline, compare, source rail | AIS/flight/sanctions unavailable until provider verified. |
| Equity Intelligence | Inspect one ticker | equity, financials, options, news | Price/volume, technicals, fundamentals, options readiness, events | Provider-required rows visible. |
| Financial Statements | Analyze fundamentals | financial statement contract | Income/balance/cashflow, ratios, earnings, segment/geography | No fake statement rows. |
| Options / GEX / Volatility | Research option structure | options quant contract | Chain quality, IV/surface, gamma proxy/GEX, scenarios | No dealer positioning claim without data. |
| Crypto Intelligence | Analyze crypto markets | crypto contract | Price/OI/funding/taker/LS, heatmaps, liquidation proxy, scenarios | Public provider/rate-limit/cache labels. |
| Screener | Find candidates | screener contract | Filters, ranking, heatmap, scatter, watchlist staging | Missing fundamentals/options fields shown as gaps. |
| Portfolio Quant | Understand exposure/risk | portfolio quant contract | Holdings, exposure, drawdown, attribution, stress, correlation | Local-only, no accounts/brokers. |
| Event Graph | Link events to assets | event graph contract | Nodes, edges, relationship matrix, evidence | Inferred/proxy labels visible. |
| News / OSINT Feed | Monitor source flow | news dashboard, feeds | Feed, map-linked events, asset links, source freshness | Rate-limit/403 rows shown honestly. |
| Reports | Produce source-bound summary | report contract | Report builder, section evidence, caveat rail, export | No advice/execution language. |
| Command Terminal | Navigate like a terminal | command workspace | Command parser, history, context, workspace actions | Provider-required commands gated. |
| Provider/Data Center | Know what is real | provider health, layers, feeds, AI providers | Health ledger, key requirements, route manifest | Missing keys and blocked sources clear. |

## 8. Map Renderer Decision Record

Decision status: not yet implemented. Phase 5C should implement the chosen option only after this decision is accepted.

| Option | Pros | Cons | Best use |
|---|---|---|---|
| Improve first-party SVG | No dependency, deterministic, easy fixture tests | Poor map feel, weak geography, no real pan/zoom/tiles/clusters | Only if dependency avoidance is mandatory. |
| Leaflet | Lightweight, mobile-friendly, simple markers/popups/tiles, large ecosystem | Raster/tile style; richer vector layers need plugins | Fastest credible WorldMonitor-like map foundation. |
| MapLibre GL JS | Vector/WebGL, clusters, realtime examples, heatmaps, popups, time sliders, advanced controls | Heavier, WebGL issues, SSR/client-only complexity | Best long-term map-first terminal path. |
| D3/TopoJSON | Full custom rendering and offline control | More custom engineering, weaker out-of-box map interactions | Custom thematic/choropleth layers after product basics. |

Recommendation:

- Phase 5C should choose either Leaflet for speed or MapLibre for long-term product quality.
- For this product, MapLibre is the stronger final direction if bundle and client-only integration are acceptable.
- Use OpenStreetMap or other tile sources only with correct attribution and no paid token assumptions.
- Keep the current SVG map as a fallback/offline fixture renderer.

Required map acceptance:

- Pan/zoom works.
- Marker click opens source/caveat/details.
- Layer toggles update markers.
- Timeline filter changes marker visibility.
- News/event list is linked to map marker selection.
- Approximate/static/proxy coordinates are visibly labeled.
- Mobile layout does not collapse marker/details rails.

## 9. Chart Renderer Decision Record

Decision status: not yet implemented. Phase 5C should implement the chosen option only after official docs/license review.

| Option | Pros | Cons | Best use |
|---|---|---|---|
| Existing native SVG | No dependency, deterministic fixtures, simple tests | Distortion, poor axes/tooltip/layout, no pro chart UX | Sparklines and small status charts only. |
| Financial chart package | Candles, volume, crosshair, overlays, multi-panel support | Needs docs/license/bundle review | Main TradingView-like price workspace. |
| General chart library | Many chart types, tables/heatmaps/bar/line | May be less finance-specific | Portfolio, financials, screeners, reports. |
| External widgets | Quick visual supplement | Not controllable, provider/data ambiguity, not testable as source | Optional display-only panel, never calculation source. |

Recommendation:

- Keep native SVG only for fallback and small cards.
- Adopt a reviewed chart stack for main market/equity/crypto/portfolio workspaces.
- Before install, document license, SSR strategy, client component boundary, bundle impact, test approach, and visual regression path.

Required chart acceptance:

- Correct axes and non-distorted positioning.
- Tooltip/crosshair or readable data labels for desktop.
- Mobile layout remains legible.
- Multi-series and compare overlays work.
- Every chart shows provider, freshness, caveat, and data gap.
- Fixture data cannot be mistaken for live market data.

## 10. Source-Bound Research Report Architecture

The external Gold Quant Regime report is useful as a structure reference, but not as product advice.

Adopt as non-advisory research sections:

1. Executive summary.
2. Market snapshot.
3. Asset/instrument context.
4. Futures/positioning context where provider-backed.
5. Options/GEX/volatility dashboard where provider-backed or explicitly unavailable.
6. Macro regime.
7. News/geopolitical risk.
8. Event calendar.
9. Technical/market-structure context.
10. Timeframe alignment as observation only.
11. Risk/liquidity context.
12. Regime scoring model.
13. Scenario matrix.
14. Data sources and confidence.
15. Caveats and data gaps.

Must rewrite or block:

- `Final Action`
- `Preferred Direction`
- `Recommended Leverage`
- `Long Entry Zone`
- `Short Entry Zone`
- `Stop Loss`
- `Take Profit`
- `Position Size`
- `Execution Permission`
- broker/execution/order-routing language

Replacement language:

- `research scenario`
- `evidence condition`
- `invalidating evidence`
- `risk context`
- `data gap`
- `confidence and source caveat`
- `not financial advice`

Architecture target:

- `lib/research_report_workstation.py` or similar contract builder.
- Consume market/equity/crypto/options/map/news/provider contracts.
- Emit JSON-safe report sections plus markdown export.
- Gemini can summarize only from source-bound context; when unavailable, use deterministic rule-based summary.
- Add sanitizer tests for advice/execution forbidden phrases.

## 11. Phase 5C/5D/5E Implementation Backlog

### Phase 5C: Runtime And Renderer Foundations

Objective:

- Stop relying on fixture-only market/equity/crypto/map views.
- Add runtime mode controls and choose/install first real chart/map foundation if license/docs pass.

Vertical slices:

1. Runtime mode switch
   - Files: `lib/api_contracts.py`, `backend/api/app.py`, `apps/web/src/lib/fixtures.ts`, `apps/web/src/app/page.tsx`.
   - Modes: `fixture`, `cache`, `live-if-available`.
   - Tests: provider failure fallback, no fake live rows, route query parsing.

2. Chart foundation
   - Files: `apps/web/package.json`, chart components, `lib/chart_specs.py`.
   - Tests: chart spec validation, mobile render marker, source labels.
   - Visual: market/equity/crypto desktop and mobile screenshots.

3. Map foundation
   - Files: map component, `war-room-map` view, possible renderer decision doc.
   - Tests: markers, layer toggles, timeline filters, popups, attribution/source labels.
   - Visual: War Map desktop/mobile screenshots.

### Phase 5D: Core Product Workspaces

Objective:

- Migrate missing Streamlit capabilities to real web contracts.

Vertical slices:

1. Screener workspace
   - New payload: `screener_workspace`.
   - Reuse `lib/screeners.py` and heatmap engines.
   - UI: filters, ranked table, heatmap, scatter, source rail.

2. Portfolio quant workspace
   - New payload: `portfolio_quant_workspace`.
   - Reuse backtester, attribution, portfolio visuals.
   - UI: holdings, exposure, drawdown, attribution, stress, correlation.

3. Financial statement workspace
   - New payload: `financial_statement_workspace`.
   - Reuse financial terminal/chart engines.
   - UI: statements, margins, valuation, earnings, availability heatmap.

4. Options/GEX/volatility workspace
   - New payload: `options_quant_workspace`.
   - Reuse options chain, IV, surface, quality, options flow.
   - UI: chain readiness, IV/surface, gamma proxy/GEX with caveat, scenarios.

### Phase 5E: Reports, Commands, Retention Hooks

Objective:

- Make the product useful every day and able to explain what changed.

Vertical slices:

1. Source-bound research report generator
   - New payload: `research_report`.
   - Gold report structure adapted into non-advisory form.
   - Tests: no forbidden advice/execution text, source coverage, data gaps.

2. Command terminal deepening
   - Commands route into specific symbol/workspace states.
   - Add command history and context preview.
   - No execution/order-routing.

3. Watchlist and alert readiness
   - Local-only readiness first.
   - No hosted auth/billing/persistence until product contracts are stable.

## 12. Success Criteria For The Next Coding Slice

The next implementation slice is successful only if:

- At least one major surface stops being fixture-only by default when free/public data is available.
- Or the map/chart renderer foundation is upgraded with documented license/docs review and visible render verification.
- Tests prove unavailable and provider failure states are honest.
- Visual screenshots show corrected chart layout and/or real map behavior.
- The final response states which rows are live, cached, stale, fixture, proxy/static, missing-key, or unavailable.

A decorative panel with static fixture rows is not success.
