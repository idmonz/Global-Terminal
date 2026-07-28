# External Runtime Adoption Roadmap

Updated: 2026-06-22

This document replaces the prior "concept-only" posture for the requested external references with an implementation-oriented adoption plan. The goal is not to clone the external projects. The goal is to make the Streamlit terminal behave like a real daily-use intelligence and market workstation: live/source-labeled data, command workflows, quant diagnostics, maps, news, briefs, and visual analysis.

## Scope Studied

`external (2).zip` was unpacked for analysis under `review_workspace/external2_analysis`. The target projects were:

| Project | Files / lines observed | Primary value | Adoption stance |
|---|---:|---|---|
| worldview | 4,130 files / 310,667 lines | NASA GIBS/OpenLayers layer model, time navigation, compare tools, natural-event map UX | Clean-room UX and data-model reference only; NASA license needs caution |
| worldmonitor | 3,136 files / 916,615 lines | feed registry, risk layers, CII scoring, brief engine, cache/freshness model, map variants | Clean-room reimplementation of patterns; AGPL source must not be copied |
| OpenBB | 1,932 files / 1,614,615 lines | financial data platform, standard models, provider contracts, API server option | Use as optional installed backend/API; no vendored source copy |
| BB-Terminal | 44 files / 5,913 lines | Bloomberg-style command codes, OpenBB API path mapping, transparent signal rules | Recreate command/signal logic natively; verify license before direct excerpts |
| bloomberg-terminal | 118 files / 14,125 lines | dense terminal layout, keyboard shortcuts, watchlist state, React Query/Jotai patterns | Use UI interaction concepts only; its market data route is simulated/fallback-heavy |
| osiris | 128 files / 28,950 lines | keyless OSINT APIs, MapLibre layers, flights, earthquakes, Telegram/RSS fallback, sanctions cache | MIT-licensed source can inform direct reimplementation with attribution where needed |

The current Streamlit app was also inspected: 814 Python files, about 43,343 lines.

## Why The Current App Feels Like A Mock

The app has many terminal-shaped modules, but several runtime paths explicitly stop at reference, proxy, or fallback states:

- `app.py:480` labels the WorldMonitor panel as "Design reference only; runtime code stays inside this app."
- `lib/worldmonitor_adapter.py:68` says WorldMonitor is "optional and reference-only; runtime code does not import external source."
- `lib/live_feeds.py:47`, `lib/live_feeds.py:61`, `lib/live_feeds.py:85`, `lib/live_feeds.py:94`, and `lib/live_feeds.py:102` return "No requester supplied" for GDELT, USGS, Binance, and CoinGecko unless an external caller injects a requester.
- `lib/data_router.py:300-302` maps `news.*` / `osint.events` to `build_event_stream()` with no real news input and marks it estimated/proxy.
- `lib/war_room.py:182-187` builds an "Energy Risk Proxy" from static/proxy chokepoint logic unless live providers are explicitly configured.
- Existing docs such as `EXTERNAL_REFERENCE_MASTER_UTILIZATION_ROADMAP.md` kept most external material as concept-only, so the implementation naturally stayed shallow.

Conclusion: the product already has a shell, taxonomy, and caveat system. It needs a real runtime data spine and a stricter "no fake success" policy.

## External Logic To Adopt

### 1. Data Spine And Provider Truth

Adopt from OpenBB and WorldMonitor:

- A single provider contract: request, source, endpoint, provider, freshness, cached flag, confidence, data gaps, and license/caveat metadata.
- A source router that can use OpenBB when installed or when an `openbb-api` server is running, but still exposes native keyless providers.
- A health ledger like WorldMonitor `api/health.js`: every panel must show whether data is live, cached, stale, key-missing, estimated, or unavailable.
- A hard ban on UI panels rendering "fresh" when the upstream timestamp is missing.

Immediate targets:

- Replace passive requester hooks in `lib/live_feeds.py` with real, timeout-bounded request functions.
- Extend `lib/data_router.py` so `news.world`, `osint.events`, `natural.earthquakes`, `aviation.flights`, `sanctions.search`, and `crypto.market` return real datasets by default where keyless sources exist.
- Add single-flight TTL cache around expensive OSINT calls.

### 2. Terminal Command System

Adopt from BB-Terminal:

- Treat command codes as first-class actions, not page links only.
- Implement `CC`, `HELP`, `DES`, `GP`, `QR`, `HP`, `FA`, `KEY`, `DVD`, `EE`, `NI`, `OMON`, `WEI`, `MOV`, `CURV`, `FXC`, `CRYPTO`.
- Let commands open or update a persistent workspace tab/session state.
- Add command history, autocomplete, active symbol context, and error suggestions as real state, not only sidebar text.

Implementation target:

- Expand `lib/terminal_function_registry.py` and `lib/terminal_command_router.py` from routing metadata into executable payload builders.
- Make `AAPL FA` load financial data immediately, `CURV` load a rates curve, `NI` load company/world news, and `OMON` load a real options chain or explicit provider gap.

### 3. Transparent Signal Engine

Adopt from BB-Terminal `signals.ts`:

- Moving-average, 52-week range, P/E, forward P/E, EV/EBITDA, margin, growth, analyst upside, analyst recommendation, leverage, and dividend checks.
- Each signal returns `{level, label, detail, evidence, source_status}`.
- The verdict is a tally of transparent rules, not an opaque prediction.

Implementation target:

- Add `lib/equity_signal_rules.py`.
- Feed it from OpenBB/yfinance financial statements and price history.
- Show sparse/insufficient-data states honestly.

### 4. Keyless OSINT Runtime

Adopt from osiris:

- USGS earthquake feed with 24h M2.5+ and cache headers.
- adsb.lol regional aircraft polling with classification and GPS-jamming aggregation.
- Telegram public preview parsing with RSS fallback, but with safer parser boundaries and source labels.
- OpenSanctions SDN lookup with 24h TTL, single-flight cache, and exact vs fuzzy search modes.

Implementation target:

- Add `lib/osint_sources.py` and tests.
- Wire into `pages/14_War_Room.py`, `pages/6_News.py`, `pages/17_Data_Provider_Center.py`.
- Every OSINT row must carry `provider`, `source_url`, `fetched_at`, `freshness`, `confidence`, `coordinate_method`, and `data_gap`.

### 5. Map And Layer System

Adopt from WorldMonitor, osiris, and worldview:

- Layer registry with group, icon, renderer support, source requirement, key requirement, default state, and caveat.
- Map-first War Room with layer counts and source status, not static cards first.
- Time controls and comparison mode from worldview concepts: now, last 24h, last 7d, custom window; compare before/after event windows.

Implementation target:

- Replace current static/proxy layer declarations with a Python `LayerDefinition` registry.
- Add `natural.earthquakes`, `aviation.flights`, `osint.news`, `sanctions`, `chokepoints`, `market_reactions`, and `energy`.
- Keep Plotly/Mapbox for Streamlit MVP; evaluate `streamlit-folium` or a local MapLibre component later.

### 6. Daily Brief And News Intelligence

Adopt from WorldMonitor:

- Curated feeds by category and source type.
- Source propaganda/risk profile and source tiering.
- Daily market brief combining markets, news, regime, yield curve, sectors, and watchlist.
- Fallback summary only when clearly labeled rule-based.

Implementation target:

- Build `lib/feed_registry.py` from safe public RSS/GDELT sources.
- Replace placeholder `build_worldmonitor_style_news_dashboard([])` calls with real feed ingestion.
- Add "What changed since last open" briefs using local cache snapshots.

### 7. Quant And Visualization Workstation

Adopt from OpenBB and the existing Goal 12/13 work:

- Use OpenBB endpoints for equity, ETF, rates, macro, options, commodities where available.
- Keep native yfinance/FRED/pykrx fallback, but route through one data contract.
- Add factor and risk diagnostics: returns, drawdown, volatility, correlation, beta, regime buckets, walk-forward quality, option surface QA.

Implementation target:

- Make `Portfolio Quant Lab` and `Financial Terminal` command-driven.
- Build reusable visual payloads rather than page-local charts.
- Add "data quality score" beside every chart.

## License And Compliance Boundary

This is not legal advice; it is the engineering boundary for implementation:

- WorldMonitor and OpenBB are AGPL-family. Do not copy source into this repo. Use OpenBB as a user-installed package/API and reimplement WorldMonitor-like behavior independently.
- worldview uses the NASA Open Source Agreement. Treat as behavior/UX/reference only unless a separate license review is approved.
- osiris is MIT. Small direct logic adaptation is possible with attribution and retained notice, but prefer project-native reimplementation.
- bloomberg-terminal README says MIT, but its data route is simulated. Use layout/interaction ideas, not runtime data logic.
- BB-Terminal has no separate license file in the inspected tree; README says the terminal code is yours to relicense while OpenBB is AGPL. Treat direct copying as blocked until license is verified. Behavior reimplementation is acceptable.

## Source-To-Implementation Matrix

The external code should be consumed through traceable evidence cards, not through vague "inspired by" claims. Each implementation task should name the inspected source file, line range, extracted behavior, local target module, license stance, and acceptance test.

| External source area | Behavior to extract | Local implementation target |
|---|---|---|
| `worldview/web/js/map/*`, `web/js/layers/*`, timeline and compare containers | Layer lifecycle, temporal navigation, compare-window UX, source-backed map controls | `lib/layer_registry.py`, War Room timeline filters, compare mode |
| `worldmonitor/src/config/feeds.ts` | Curated feed taxonomy, source grouping, source risk/tier metadata | `lib/feed_registry.py`, `pages/6_News.py`, overview brief |
| `worldmonitor/src/config/map-layer-definitions.ts` | Declarative layer registry with renderer, defaults, requirements, and caveats | `lib/layer_registry.py`, `pages/14_War_Room.py` |
| `worldmonitor/src/services/daily-market-brief.ts` | Multi-source daily brief assembly and "what changed" framing | `lib/daily_brief.py`, first-screen intelligence summary |
| `worldmonitor/src/services/cached-risk-scores.ts` | Freshness-aware risk cache, no fake live state | `lib/runtime_cache.py`, `lib/unified_data_layer.py` |
| `worldmonitor/src/services/cross-source-signals.ts` | Convergence scoring across unrelated signals | `lib/cross_source_signals.py`, War Room risk engine |
| `worldmonitor/api/health.js`, `server/gateway.ts` | Provider health, cache status, gateway timeout boundaries | `pages/17_Data_Provider_Center.py`, `lib/data_router.py` |
| `OpenBB/openbb_platform/core/openbb_core/provider/standard_models/*` | Typed market data contracts for equity, options, treasury, news | `lib/openbb_bridge.py`, `lib/data_contracts.py` |
| `OpenBB/openbb_platform/core/openbb_core/api/rest_api.py`, router/provider registry/query executor | Local OpenBB API mode and provider routing model | OpenBB direct/API adapter, terminal command execution |
| `BB-Terminal/app/src/lib/functions.ts` | Bloomberg-style command grammar and endpoint mapping | `lib/terminal_function_registry.py`, `lib/terminal_command_router.py` |
| `BB-Terminal/app/src/lib/signals.ts` | Transparent equity rule engine with explainable verdicts | `lib/equity_signal_rules.py`, Financial Terminal |
| `BB-Terminal/app/src/lib/workspaceStore.ts`, command bar components | Persistent tabs, command history, active symbol context | Streamlit session state command workspace |
| `bloomberg-terminal/components/bloomberg/*`, hooks, keyboard shortcuts, watchlist | Dense layout, keyboard flow, watchlist interactions | UI layout patterns only; no simulated data reuse |
| `bloomberg-terminal/app/api/market-data/route.ts` | Fallback/simulation anti-pattern to avoid in production data panels | Provider truth audit tests |
| `osiris/src/app/api/earthquakes/route.ts` | USGS keyless earthquake feed, cache discipline | `lib/osint_sources.py`, War Room natural events |
| `osiris/src/app/api/flights/route.ts` | adsb.lol regional polling, aircraft classification, GPS-jamming aggregation | `lib/osint_sources.py`, aviation layer |
| `osiris/src/app/api/news/route.ts` | Telegram public preview plus RSS fallback and coordinate approximation | `lib/feed_registry.py`, `lib/osint_sources.py` |
| `osiris/src/lib/sanctions.ts` | OpenSanctions CSV cache, exact/fuzzy lookup, 24h TTL | `lib/sanctions_source.py`, sanctions command/layer |
| `osiris/src/components/OsirisMap.tsx`, `LayerPanel.tsx` | Map layer grouping, toggles, marker inspection workflow | War Room map layer UI |

## Line-By-Line Adoption Protocol

For every external-derived feature, create a short evidence card before coding:

1. Source proof: external project, file path, exact line range, and what the code actually does.
2. License stance: direct use allowed, behavior-only, or blocked pending review.
3. Local design: target module, data contract, UI surface, and state model.
4. Runtime source: live endpoint, cache TTL, timeout, retry, and stale behavior.
5. Acceptance: test or manual check proving the feature returns real rows or an explicit unavailable state.
6. Caveat: source label and data gap shown to the user.

This protocol is the practical version of "line-by-line analysis": every useful external line becomes either an implementation task, a rejected pattern, or a compliance note. Nothing should be adopted as a visual theme alone.

## Commercial B2C Track: Beyond Streamlit

This section is added after reviewing the external projects and the current codebase shape. The current first-party code outside the extracted external workspace is approximately:

| Area | Count |
|---|---:|
| `app.py` | 1 file / 511 lines |
| `pages/` | 24 files / 3,661 lines |
| `lib/` | 393 files / 30,138 lines |
| `tests/` | 392 files / 6,210 lines |

There is no first-party JavaScript/TypeScript web app scaffold outside the external reference trees. The runtime dependency stack is Python/Streamlit/Pandas/Plotly-first. That means the commercial path should not throw away the product engine. It should preserve the `lib/` modules and tests as the research/data backend, then replace the Streamlit presentation layer with a real web product surface.

### Why Streamlit Should Become The Lab, Not The Product

Streamlit is useful for internal research, rapid diagnostics, and analyst-only tools. It is weak for a daily B2C product that needs:

- Durable user accounts, billing, subscriptions, onboarding, and entitlements.
- Mobile-responsive interaction, installable PWA behavior, shareable links, and notification surfaces.
- Real-time command palettes, keyboard navigation, persistent workspaces, and multi-tab terminal sessions.
- WebSocket/SSE updates for alerts, market moves, provider health, and breaking events.
- MapLibre/deck.gl/globe.gl class map rendering with thousands of markers, layer toggles, timeline brushing, and compare windows.
- Product analytics, feature flags, A/B tests, retention funnels, and customer support tooling.
- Clean API boundaries for future mobile apps, partner integrations, and paid data providers.

Streamlit can remain as the internal analyst console and regression surface, but the customer-facing product should move to a web architecture.

### Recommended Commercial Architecture

Use a split product architecture:

| Layer | Recommended stack | Reason |
|---|---|---|
| Web app | Next.js + React + TypeScript | Rich B2C UX, routing, SEO/share pages, PWA, authentication integration |
| Terminal workspace | React command palette, persistent tabs, keyboard shortcuts, TanStack Query, Zustand/Jotai | Mirrors BB-Terminal/Bloomberg-style workflow better than Streamlit reruns |
| Map/visualization | MapLibre GL, deck.gl, globe.gl, Plotly.js/ECharts where useful | Matches worldmonitor/osiris/worldview map-first interaction patterns |
| Backend API | FastAPI + Pydantic contracts | Reuses current Python data/quant modules while creating stable JSON APIs |
| Background jobs | Celery/RQ/Arq + Redis | Scheduled briefs, provider probes, alerts, cache refresh, slow OSINT calls |
| Data store | Postgres + TimescaleDB where time-series volume grows; SQLite allowed only for local dev | User accounts, watchlists, alerts, reports, snapshots, source freshness |
| Cache | Redis + local fallback | TTL, single-flight fetches, provider health, stale replay |
| Auth/billing | Clerk/Auth.js/Supabase Auth + Stripe | B2C onboarding, subscription tiers, usage metering |
| Deployment | Docker Compose for dev; Vercel/Render/Fly/Railway or cloud VM for early production | Keeps web/API/worker/cache separable |

The Python engine should expose typed API payloads rather than DataFrames as UI contracts. DataFrames can remain internal, but API boundaries should use JSON-safe records with source, freshness, caveat, quality, and license metadata.

### B2C Product Proposition

The product should not be sold as "a dashboard." The B2C value should be:

- A daily geopolitical-market intelligence cockpit for serious retail investors, founders, analysts, and crypto/macro users.
- A source-labeled cross-asset brief that explains what changed overnight, which assets are linked, and which data is missing.
- A command-driven research terminal where a user can type `AAPL FA`, `CURV`, `BTC CRYPTO`, `REDSEA WAR`, or `KOREA RISK` and land on a real workspace.
- A map-first risk room that connects events, chokepoints, earthquakes, sanctions, energy, crypto, rates, equities, and watchlists.
- A research notebook that turns event chains into saved briefs, watchlist alerts, and shareable but caveated reports.
- A transparent quant layer: no opaque "buy/sell" predictions, only explainable diagnostics, scenarios, source quality, and uncertainty.

### B2C Feature Pillars

1. Onboarding: choose watchlist assets, regions, risk themes, crypto/energy/equity preference, and notification cadence.
2. Daily Brief: one screen answering "what changed, why it matters, affected assets, source quality, missing data."
3. Event-to-Asset Graph: convert news/OSINT events into linked tickers, commodities, FX, sectors, countries, and crypto exposures.
4. Terminal: command palette, workspace tabs, recent commands, saved layouts, and explainable error suggestions.
5. War Map: live/cached layer registry, time slider, compare mode, marker drilldown, and approximate-coordinate caveats.
6. Alerts: watchlist/event/risk/freshness alerts with explicit source and stale-data behavior.
7. Quant Lab: portfolio stress, factor exposure, options diagnostics, volatility surface QA, and scenario simulations.
8. Research Memory: saved reports, event timelines, strategy notes, snapshots, and "new since last open."
9. Sharing: exportable PDF/Markdown/HTML briefs with provenance and no-advice disclaimers.
10. Trust Center: provider health, coverage, source risk, data gaps, and historical uptime.

### Migration Roadmap

This commercial track should run after the Phase 1 runtime-data slice proves real source-backed value.

#### Commercial Phase A: API-Ready Python Core

- Keep Streamlit pages operational.
- Identify UI-independent functions in `lib/` and wrap them in Pydantic response models.
- Add `services/api` or `backend/api` with FastAPI endpoints for overview, war room, news, terminal commands, provider health, watchlists, reports, and quant payloads.
- Add serialization tests proving no endpoint returns raw DataFrames, unserializable timestamps, private paths, or unlabeled proxy data.

Acceptance:

- `GET /api/overview`, `GET /api/war-room`, `GET /api/news`, `POST /api/terminal/command`, and `GET /api/provider-health` return stable JSON.
- The Streamlit app and FastAPI backend consume the same Python data contracts.

#### Commercial Phase B: First Web Shell

- Create a first-party `apps/web` Next.js project.
- Build the terminal frame: top command bar, left workspace rail, central panel, right intelligence rail, bottom provider/freshness strip.
- Implement Overview, Daily Brief, War Room map, Provider Health, and Terminal Command result views.
- Use fake UI data only in Storybook/dev fixtures; live app routes must call the backend or show explicit unavailable states.

Acceptance:

- A user can open the web app, run a command, inspect a map layer, open a brief, and see source freshness without touching Streamlit.

#### Commercial Phase C: Personalization And Retention

- Add user auth, watchlists, saved regions, saved commands, report history, and alert preferences.
- Add daily snapshot memory and "new since last open."
- Add notification delivery: email first, then push/webhook later.
- Add product analytics for activation and retention.

Acceptance:

- The product can explain why a user should come back tomorrow.
- Watchlist-specific events and source freshness are persisted per user.

#### Commercial Phase D: Paid Product Readiness

- Add Stripe subscriptions and usage caps.
- Define tiers:
  - Free: delayed/basic brief, limited watchlist, limited map layers.
  - Pro: full daily brief, alerts, saved reports, command workspace, quant diagnostics.
  - Premium: advanced OSINT layers, OpenBB-backed factor/rates/options, larger history, export pack.
- Add terms, privacy, data-source notices, no-advice language, and audit logs.
- Add provider cost controls and per-tier entitlements.

Acceptance:

- A paying user can subscribe, receive value daily, and understand exactly which data is live, cached, estimated, or unavailable.

### What To Reuse vs Replace

Reuse:

- `lib/data_contracts.py`, `lib/data_router.py`, `lib/unified_data_layer.py`, OpenBB adapters, provider probes, quant modules, report engines, alert engines, watchlist/store logic, source freshness, data quality, and tests.

Replace or demote:

- Streamlit page layout code, sidebar navigation, `st.session_state` as the primary state model, `unsafe_allow_html` visual fragments as the customer UI, and page-local chart construction.

Preserve as internal tools:

- Streamlit pages can become analyst/admin workbench pages for provider probes, local quant experiments, regression checks, and fast prototyping.

### Commercial Quality Gates

- No panel may show "live" without upstream timestamp or freshness metadata.
- No customer-facing route may depend on a paid key unless the missing-key state is explicit.
- No AGPL/NASA/reference source may be copied into the proprietary product without a license decision.
- Every B2C chart, map marker, alert, and brief must carry source and caveat metadata.
- AI summaries must be optional, neutral, source-bound, and must not generate trading instructions.
- The product must be usable without the sidebar: search, command, map, brief, watchlist, and alerts are primary flows.

## Product Roadmap

### Phase 0: Truth Audit And Acceptance Gates

Deliverables:

- Add a "mock/proxy/fallback audit" test that fails when primary pages label simulated/proxy data as live.
- Add provider readiness tests for OpenBB, yfinance, RSS, GDELT, USGS, adsb.lol, OpenSanctions, Binance/CoinGecko.
- Add a visible "Runtime Data Mode" strip: live, cached, stale, key-missing, proxy, unavailable.

Acceptance:

- War Room can no longer show only static chokepoint rows while claiming real intelligence.
- Overview can no longer call a panel "WorldMonitor-style" without source-backed rows or an explicit unavailable state.

### Phase 1: Real Keyless Intelligence Core

Deliverables:

- `lib/osint_sources.py`: USGS, GDELT/RSS, Telegram/RSS fallback, OpenSanctions, adsb.lol, CoinGecko/Binance public endpoints.
- `lib/runtime_cache.py`: TTL + single-flight cache.
- `lib/feed_registry.py`: curated public feed catalog with source tier and source risk.
- Tests for parser behavior, timeouts, cache reuse, and empty-source handling.

Acceptance:

- `War Room` opens with at least earthquakes, public news/RSS, chokepoints, market-linked events, and explicit unavailable live AIS/flight layers.
- If a keyless provider fails, the UI shows the provider error and stale/cache fallback instead of fake rows.

### Phase 2A: Source-Backed Runtime Contracts

Status: implemented in the Streamlit/Python runtime slice on 2026-06-16.

Deliverables completed:

- Added `lib/feed_registry.py` as an import-safe curated taxonomy for RSS, GDELT, USGS, CoinGecko, Binance, static chokepoints, sanctions, AIS, and flight provider slots.
- Routed public RSS defaults through the feed registry so default news feeds are no longer only scattered inside news ingestion code.
- Added provider health ledger helpers in `lib/provider_health_engine.py` that classify runtime evidence as `live/fresh`, `cached`, `stale`, `rate-limited`, `forbidden/subscription-blocked`, `missing-key`, `unavailable`, or `proxy/static`.
- Added layer runtime contracts in `lib/layer_registry.py` with row counts, fetched timestamps where known, freshness/source status, key requirements, caveats, and recommended actions.
- Wired War Room state and Streamlit surfaces to show layer runtime contracts and provider health ledger rows.
- Wired News and Data Provider Center surfaces to expose the curated feed registry and recent runtime health ledger.
- Kept sanctions as registry-only/unavailable in this slice. No sanctions rows are fetched or displayed as live.
- Preserved AIS and flight tracking as explicit missing-key/unavailable layer states unless real providers are configured and probed.

Remaining gaps:

- Phase 2B has since added the API-ready Python contract layer and optional backend surface.
- Next.js `apps/web`, auth, billing, entitlements, and paid provider workflows remain future commercial-track work.
- OpenSanctions lookup remains a future source-backed implementation task.
- Map timeline/compare mode remains a future layer interaction task.
- Layer payloads are API-ready dictionaries today and are also represented through the Phase 2B API contract envelope.

### Phase 2B: API-Ready Contract Boundary

Status: implemented on 2026-06-16.

Deliverables completed:

- Added `lib/api_contracts.py` with JSON-safe API envelopes for feed registry, provider health, layer runtime, news dashboard, War Room, AI provider status, and route manifest payloads.
- Added `docs/PHASE_2B_API_CONTRACT_SPEC.md` documenting contract version `phase_2b.v1`, payload families, serialization rules, unavailable/error semantics, and optional backend behavior.
- Added optional import-safe `backend/api/app.py` with read-only route getters and FastAPI routes when FastAPI is installed.
- Added `requirements-api.txt` so FastAPI/Uvicorn stay outside the base Streamlit requirements.
- Added `tests/test_api_contracts.py` covering JSON serialization, DataFrame/DataResult/datetime boundary conversion, secret redaction, unavailable states, Gemini free-first status, War Room payload safety, and optional backend import safety.

Remaining gaps:

- Streamlit pages still mostly consume legacy internal payloads directly; the API contract builders are available but not yet the primary page boundary.
- Static JSON fixtures for future web-shell development have not yet been exported.
- There is no first-party `apps/web` project because Node/npm are not currently available in the environment.
- Optional FastAPI route smoke tests through `TestClient` are not active unless FastAPI is installed.
- Auth, billing, entitlements, user accounts, web notifications, and paid-provider tiering remain future B2C work.

### Phase 2C: Contract Adoption And Web-Shell Readiness

Status: implemented on 2026-06-16.

Deliverables completed:

- Added `docs/PHASE_2C_CONTRACT_ADOPTION_SPEC.md` explaining how Streamlit, optional FastAPI, static fixtures, and a future web app consume the same Phase 2B payloads.
- Added `scripts/export_api_fixtures.py`, a deterministic, network-free API fixture exporter for feeds, provider health, layers, news, War Room, AI provider status, and route manifest JSON.
- Exported static fixtures under `static/api-fixtures/`: `feeds.json`, `provider-health.json`, `layers.json`, `news.json`, `war-room.json`, `ai-providers.json`, and `manifest.json`.
- Added thin Streamlit contract payload preview panels to War Room, News, and Data Provider Center while keeping payload assembly in `lib/`.
- Added optional backend route smoke coverage in `tests/test_api_backend_routes.py` that passes whether FastAPI is installed or absent.
- Added `docs/PHASE_2C_WEB_SHELL_READINESS.md` mapping future React/Next.js shell routes to exported fixtures and optional API routes.
- Added fixture exporter coverage in `tests/test_api_fixture_export.py` and compact contract preview helper coverage in `tests/test_api_contracts.py`.

Acceptance completed:

- Fixture export produces valid JSON that passes `validate_api_payload`.
- No fixture or API payload leaks raw DataFrames, datetimes, DataResult objects, Plotly figures, Streamlit objects, local private paths, or secrets.
- Streamlit remains functional and starts consuming the same contract builders future web clients will use.
- OpenSky remains explicit unavailable/error until OAuth and `/states/all` fetch succeed.
- Gemini remains free-first and key-safe.

Remaining gaps:

- Node/npm/npx are still not available in this environment, so a real `apps/web` scaffold remains deferred.
- FastAPI remains optional and is not added to base `requirements.txt`; route tests skip HTTP `TestClient` when the dependency is absent.
- Static fixtures are development fixtures, not live source coverage claims.
- Auth, billing, entitlements, user accounts, web notifications, and paid-provider tiering remain future B2C work.

### Phase 2D: Fixture-Backed Web Shell Kickoff

Status: implemented on 2026-06-16.

Deliverables completed:

- Verified `node`, `npm`, and `npx` availability:
  - `node v24.16.0`
  - `npm 11.13.0`
  - `npx 11.13.0`
- Created a first-party `apps/web` Next.js/React/TypeScript shell that loads `static/api-fixtures/` first.
- Added TypeScript envelope types and fixture loading for the `phase_2b.v1` API contract without changing the Python payload contract.
- Built initial Manifest, War Room, News, Provider Health, Layers, Feeds, and AI Provider panels from fixtures.
- Added `apps/web/scripts/validate-fixtures.mjs` and `npm --prefix apps/web test` to validate the shared fixture envelope shape.
- Kept live backend wiring optional; fixture fallback remains the default development mode.
- Added `docs/PHASE_2D_WEB_SHELL_REPORT.md` with toolchain, dependency, runtime, and verification results.

Acceptance completed:

- The web shell exists and builds without paid keys or live providers.
- Static fixtures render unavailable/error/caveat states visibly.
- No generated web code copies AGPL/NASA external source.
- No route assumes OpenSky/AIS/sanctions/premium data is live.

Remaining gaps:

- Browser visual verification was limited by the unavailable in-app browser connector in the implementation session; HTTP render checks and build checks passed.
- Live FastAPI wiring remains optional/off.
- Auth, billing, entitlements, database persistence, and commercial user accounts remain future B2C work.

### Phase 2E: External Reference Deep Audit And First Product Adoption Slice

Status: implemented on 2026-06-16.

Deliverables completed:

- Added `scripts/audit_external_references.py`, a deterministic zip-audit pipeline for `external (2)/external/*.zip`.
- Generated Phase 2E artifacts under `review_workspace/external2_analysis/phase2e/`:
  - `external_zip_inventory.json`
  - `external_license_matrix.json`
  - `external_feature_candidates.json`
  - `external_line_inventory.json`
  - `external_web_license_evidence.json`
- Scanned all 18 refreshed archives, including `supabase`, `dexter`, `helix-db`, and `FinanceDatabase`.
- Indexed 32,428 zip file entries and 4,466,238 non-vendored text/code lines with compact hashes where practical.
- Created `docs/PHASE_2E_EXTERNAL_REFERENCE_AUDIT.md` with license matrix, evidence-card summary, web cross-check notes, and the source-to-local implementation decision.
- Implemented the first legally safe product slice: a FinanceDatabase-inspired asset-universe/reference-schema contract.
- Added native `lib/asset_universe.py`, `build_api_asset_universe_payload()`, optional `/api/asset-universe`, deterministic `static/api-fixtures/asset-universe.json`, and a Next.js `asset-universe` workspace view.

Acceptance completed:

- Every external archive appears in the inventory and license/readme matrix.
- Every serious adoption candidate has source evidence with file path, line range, observed behavior, license stance, local target, tests, value, and caveat.
- Blocked or unclear-license code was not copied. BB-Terminal remains blocked; Bloomberg-terminal and Dexter are README-only MIT and remain needs-review for direct copying; AGPL/NASA sources remain behavior-only.
- The web shell remains fixture/API-contract driven and shows the asset universe as `reference-schema`, not live security-master coverage.
- Fixture and contract tests cover the new payload and no external row data is copied.

Remaining gaps:

- Asset universe rows are not live. Provider-backed symbol universe imports, search, and watchlist persistence remain future work.
- HelixDB has mixed local license evidence: Apache-2.0 root plus an AGPL-3.0 metrics subcomponent. Use only separately reviewed paths or clean-room graph behavior.
- Supabase-inspired account/watchlist/auth/billing readiness is documented as future architecture only; no hosted dependency is added.
- Browser visual verification still depends on local browser tooling availability during the implementation session.

### Phase 2F: Event-To-Asset Graph Contract

Status: implemented on 2026-06-17.

Deliverables completed:

- Added `lib/event_asset_graph.py`, a clean-room graph builder that links War Room/news/provider rows to events, regions, risk themes, sectors, commodities, FX pairs, crypto pairs, providers, commands, and Phase 2E asset-class nodes.
- Added `build_api_event_asset_graph_payload()` under the existing `phase_2b.v1` envelope format.
- Added optional backend getter/route: `get_event_asset_graph_payload()` and `GET /api/event-asset-graph`.
- Exported deterministic `static/api-fixtures/event-asset-graph.json`.
- Added the Next.js `event-graph` workstation view with a persistence strip, relationship matrix, node tape, and command suggestions.
- Added `docs/PHASE_2F_EVENT_ASSET_GRAPH_SPEC.md`.
- Kept graph persistence, live graph storage, hosted Supabase, graph databases, auth, billing, and user-specific graph state explicitly unavailable.

External evidence applied:

- HelixDB: graph/query mental model only; no copied source.
- Supabase: future persistence/readiness architecture only; no hosted dependency.
- WorldMonitor/OpenBB: behavior-only source/provenance and provider-contract patterns because AGPL source remains blocked from copying.
- FinanceDatabase: Phase 2E MIT schema/taxonomy reference; external CSV rows remain un-copied.
- BB-Terminal: clean-room command-workstation behavior only because direct copying remains blocked.

Acceptance completed:

- Nodes and edges are JSON-safe, source-labeled, confidence-scored, and caveated.
- Inferred relationships are visibly marked as inferred/proxy and never presented as live facts.
- The fixture is deterministic, network-free, and passes the same secret/path scans as the other API fixtures.
- Tests cover graph construction, provenance fields, unavailable persistence state, API envelope validation, backend route inclusion, fixture export, and web fixture validation.
- The web shell renders the graph view without breaking existing War Room, Provider Health, News, Asset Universe, and Manifest views.

Remaining gaps:

- Commodity nodes are first-party proxy classifications because Phase 2E did not define a provider-backed commodity universe schema.
- Event-to-asset relationships are contextual and non-advisory; live impact persistence needs a reviewed provider-backed store.
- Command suggestions now feed the Phase 3 command workspace; deeper saved command tabs and authenticated persistence remain future work.

### Phase 3: Command Workspace And Terminal Actions

Status: implemented on 2026-06-17.

Deliverables completed:

- Added `lib/command_workspace.py`, a clean-room command workspace builder that turns Phase 2F `command_suggestions` into provider-gated workstation actions.
- Added support for `NI`, `MAP`, `DES`, `FA`, `GP`, `HP`, `WEI`, `CURV`, `FXC`, and `CRYPTO`.
- Added `build_api_command_workspace_payload()` under the existing `phase_2b.v1` envelope format.
- Added optional backend getter/route: `get_command_workspace_payload()` and `GET /api/command-workspace`.
- Exported deterministic `static/api-fixtures/command-workspace.json`.
- Added the Next.js `command-workspace` workstation view with command tape, graph-seeded context, provider gate matrix, action boundary, and result previews.
- Added `docs/PHASE_3_COMMAND_WORKSPACE_SPEC.md`.
- Kept market-action execution, order routing, auth, billing, hosted persistence, graph databases, paid provider dependencies, and user-specific command state explicitly unavailable.

External evidence applied:

- BB-Terminal: command-workstation behavior recreated clean-room; direct copying remains blocked.
- OpenBB: provider command-contract mental model only; AGPL source is not copied or vendored.
- WorldMonitor: provider truth/status/caveat behavior only; AGPL source remains outside this repository.
- Supabase: future persistence/readiness reference only; no hosted dependency is added.
- FinanceDatabase: Phase 2E schema/taxonomy evidence informs accepted asset/context types; external CSV rows remain un-copied.

Acceptance completed:

- Commands are JSON-safe, source/status/caveat/data-gap aware, and non-advisory.
- Provider-required commands become available only with `live/fresh` or `cached` provider evidence.
- Static fixtures show `NI` as source-backed preview, `MAP` as proxy/static, and all market/fundamental/rates/FX/crypto provider-required commands as unavailable or provider-required when live providers are absent.
- Fixture and contract tests cover graph-seeded contexts, provider gating, unavailable states, backend route inclusion, API validation, fixture export, web fixture validation, and no advisory command result text.

Remaining gaps:

- Command history and contexts are deterministic fixture-safe records, not user-specific persisted state.
- Provider-required commands do not fetch live providers inside fixture export; they depend on upstream provider health evidence.
- Daily brief and research memory belong to the next product slice.

### Phase 4: Map-First War Room

Status: implemented on 2026-06-17.

Deliverables completed:

- Added `lib/war_room_map.py`, a clean-room map-first War Room builder that turns existing War Room events, provider health, layer runtime, news-derived rows, and Phase 2F graph context into marker/layer/timeline/compare contracts.
- Added `build_api_war_room_map_payload()` under the existing `phase_2b.v1` envelope format.
- Added optional backend getter/route: `get_war_room_map_payload()` and `GET /api/war-room-map`.
- Exported deterministic `static/api-fixtures/war-room-map.json`.
- Added the Next.js `war-room-map` workstation view with schematic map stage, marker inspector, layer gates, timeline filters, compare readiness, provider matrix, and unavailable capability boundary.
- Added `docs/PHASE_4_MAP_FIRST_WAR_ROOM_SPEC.md`.
- Kept live AIS, live flight tracking, live sanctions markers, broker execution, auth, billing, hosted persistence, graph databases, paid provider dependencies, and user-specific state explicitly unavailable.

External evidence applied:

- WorldMonitor: source-status-aware map/layer/provider-health behavior only; AGPL source is not copied.
- worldview: timeline and compare-window behavior only; NASA-license source/assets are not copied.
- osiris: OSINT provider-gating behavior only; no source is vendored.
- OpenBB: provider-contract hierarchy behavior only; AGPL source is not copied or vendored.
- BB-Terminal/Bloomberg-style references: dense workstation behavior only; direct copying remains blocked.
- Phase 2F Event-To-Asset Graph: first-party graph context for related marker node IDs.

Acceptance completed:

- Markers are JSON-safe, source/provider/fetched timestamp aware, coordinate-labeled, confidence-scored, caveated, data-gap aware, and non-advisory.
- Layers carry source status, availability, row count, key requirement, freshness, caveat, data gap, and recommended action.
- Approximate, fixture, and static coordinates are visibly labeled.
- Missing AIS/flight/sanctions providers never render as live.
- Timeline filters and compare windows are schema-ready local state; saved compare sessions remain unavailable until persistence/auth is reviewed.
- Fixture and contract tests cover marker provenance, coordinate labels, provider gating, unavailable states, backend route inclusion, API validation, fixture export, web fixture validation, and no advisory marker/layer text.

Remaining gaps:

- The web map is schematic and fixture/API-contract driven; MapLibre/deck.gl or another production map/rendering strategy remains future work.
- Live AIS, live flight tracking, sanctions markers, and vessel-flow telemetry remain unavailable.
- Most Streamlit analysis surfaces are still not visible in `apps/web`: stock intelligence, crypto intelligence, financial/fundamental analysis, options/quant diagnostics, richer charting, screeners, and portfolio quant.
- Phase 5A later addressed the first web-product gap by adding market, equity, crypto, chart, command-routing, and upgraded War Map workspaces; screeners, portfolio quant, deep financials, and options/quant remain Phase 5B work.

### Phase 2: OpenBB First-Class Backend

Deliverables:

- Support two OpenBB modes: direct Python package and local `openbb-api` server at `127.0.0.1:6900`.
- Endpoint parity table for BB-Terminal functions.
- Real command execution for `FA`, `KEY`, `GP`, `QR`, `HP`, `EE`, `DVD`, `OMON`, `WEI`, `MOV`, `CURV`, `FXC`, `CRYPTO`.

Acceptance:

- `AAPL FA`, `TSLA KEY`, `CURV`, and `BTC CRYPTO` produce real data or explicit provider gaps.
- Data Provider Center shows which OpenBB commands are working today.

### Phase 3: Command Workspace

Deliverables:

- Persistent command tabs/session state.
- Active symbol context, command history, autocomplete, and workspace presets.
- Keyboard-centered flow inspired by BB-Terminal/Bloomberg UI.

Acceptance:

- A user can spend a session without navigating the sidebar: command -> panel -> drilldown -> brief -> export.

### Phase 4: War Room Map And Layer Runtime

Status: implemented in the current contract/web-shell slice; production map rendering remains future work.

Deliverables:

- Python `LayerDefinition` registry modeled after WorldMonitor/osiris.
- Map layer payloads for earthquakes, news, sanctions, chokepoints, flights where available, market reactions, and energy.
- Timeline filter and compare-window mode inspired by worldview.

Acceptance:

- Map markers are source-backed, counted, filterable, and clickable.
- Approximate coordinates are visibly labeled as approximate.

### Phase 5A: Product-Parity Intelligence Workstation

Status: implemented on 2026-06-17.

Deliverables completed:

- Product parity inventory across Streamlit pages, reusable `lib/` engines, current web workspaces, and missing customer-facing surfaces.
- Web equity/stock intelligence workspace using the existing Stock Analyzer, Financial Terminal, options/gamma proxy, technical diagnostics, scenario, and news/event context where safe.
- Web crypto intelligence workspace using the existing Binance/CoinGecko/free-first crypto derivatives, funding, open-interest, taker-flow, long/short, scenario, and heatmap logic where safe.
- JSON-safe chart specifications so `apps/web` renders actual source-labeled charts and graph surfaces, not just tables.
- War Map upgrade from schematic stage toward interactive map/layer/news/event behavior inspired by WorldMonitor/osiris/worldview, without copying AGPL/NASA source or claiming unavailable live layers.
- Terminal command routing that opens real web workspaces for stock, crypto, options, map, and news contexts.
- Optional API routes and deterministic fixtures for product parity, market intelligence, equity intelligence, and crypto intelligence.
- Chrome-headless visual verification at desktop and narrow/mobile widths after the in-app browser was unavailable.

Acceptance completed:

- `apps/web` visibly exposes the highest-value Streamlit capabilities rather than only fixture/contract previews.
- Equity, crypto, chart, map, and terminal surfaces carry provider/source/freshness/caveat/data-gap metadata.
- External behavior is adopted through evidence cards and clean-room implementation.
- No blocked source, fake live data, broker execution, auth, billing, hosted persistence, paid dependency, or trading advice is added.

Remaining gaps:

- Dedicated screener and portfolio quant workspaces remain Streamlit-only.
- Full financial statement drilldowns and full options book/volatility surface workflows remain partial.
- Production map dependency/data-source decision remains open.
- Optional live/cache runtime controls need tighter web integration beyond deterministic fixture export.

### Phase 5B: Product-Parity Deepening And Runtime Wiring

Deliverables:

- Dedicated screener workspace and fixture/API contract.
- Portfolio quant workspace and fixture/API contract.
- Deeper financial statement/ratio drilldowns inside the equity/financials web surface.
- Richer options/quant workspace using existing option-chain, volatility surface, scenario, payoff, and quality modules where JSON-safe.
- Runtime-mode controls that preserve deterministic fixtures while showing live/fresh, cached, stale, fixture, proxy/static, missing-key, and unavailable rows honestly.
- Map renderer decision record and minimal implementation step.

Acceptance:

- Users can move from market/equity/crypto context into screener, portfolio, financial, and options quant panels without returning to Streamlit.
- All panels remain source/status/freshness/caveat/data-gap labeled and non-advisory.
- No blocked source, fake live rows, broker execution, auth, billing, hosted persistence, user accounts, paid provider dependency, or directional market advice is added.

### Phase 5: Daily Analyst Brief

Deliverables:

- Daily market brief engine using market tape, yield curve, sector moves, watchlist, OSINT/news, and source freshness.
- Local snapshot memory: "new since last open", "risk changed", "watchlist touched by news".
- AI optional: rule-based fallback remains transparent.

Acceptance:

- The first screen answers: what changed, why it matters, what assets are linked, what data is missing, what to watch next.

### Phase 6: Quant Workstation Upgrade

Deliverables:

- Equity signal rule engine.
- Portfolio and option diagnostics powered by unified data contracts.
- Factor/regime dashboards with quality scores.
- Exportable research briefs with provenance and caveats.

Acceptance:

- Users can move from headline -> asset -> financials -> options -> portfolio exposure -> scenario without losing source context.

## Immediate Next Implementation Slice

The historical Phase 5B plan was completed and superseded by the canonical Phase 5G-5Q vertical roadmap in `docs/ROADMAP.md`.

Phase 5Q Daily Briefing And Source-Bound Research Automation is complete. It adopted external briefing behavior clean-room: WorldMonitor-style source-filtered brief discipline, OpenBB-style source-aware widgets, Bloomberg/Koyfin/TradingView daily-workspace expectations, and external `agent-skills` process habits. It did not copy external source, CSS, prompts, assets, datasets, or runtime code.

The next coding slice is Phase 5R: Provider-Backed Daily Brief Depth And Chart Drilldowns.

1. Expand the Daily Brief with official/free-first macro, rates, commodity, crypto, weather and Korean market sources.
2. Add compact source-labeled sparkline/chart drilldowns so the brief is not only a text ledger.
3. Preserve claim-to-source links and block unsupported AI/advice language.
4. Keep external report/terminal references behavior-only unless an exact permissive path is reviewed.
5. Visually verify current/cache/provider-failure, desktop, tablet, mobile, chart and source-drawer states.

## Next Execution Prompt

The next implementation prompt is stored at `docs/NEXT_ROADMAP_EXECUTION_PROMPT.md`. As of 2026-06-23, it targets Phase 5R: Provider-Backed Daily Brief Depth And Chart Drilldowns.
