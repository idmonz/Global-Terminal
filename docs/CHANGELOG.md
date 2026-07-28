# Changelog

## Goal 10 Productization

- Added executive summary engines, workspace router, cross-asset regime matrix, reusable briefing cards, and summary-first Overview integration.
- Added native command UX with function registry, parser/router, command history, and neutral INTEL-style scorecards.
- Added safe `.env` loader, masked environment status table, blank `.env.example` placeholders, and VS Code env-file guidance.
- Added dry-run provider probe runner/store/visuals, provider health engine, and Data Provider Center/OpenBB Data Hub probe panels.
- Added no-key/free provider catalog and adapters for SEC, Treasury Fiscal Data, World Bank, SDMX, GDELT, USGS, Open-Meteo, NWS, NOAA AccessAIS, Binance public, DefiLlama, and CoinGecko public.
- Expanded Portfolio Quant Lab with Alpha Combination Search, Ensemble Builder, Regime Performance, Risk Budgeting, and Data Quality tabs.
- Updated release hygiene to exclude provider probe JSON, `.env.*` secrets, external source archives, caches, pycache, logs, and private data.
- Added Goal 10 docs and offline tests.

## Goal 7 Portfolio Quant Lab / Provider Center / Terminal UX

- Added `pages/16_Portfolio_Quant_Lab.py` and Portfolio Quant modules for editable portfolios, save/load, backtests, strategy candidates, alpha signals, optimizers, forecasts, attribution, visuals, and stress integration.
- Added `pages/17_Data_Provider_Center.py` and provider modules for registry, diagnostics, live-feed status, realtime connector skeletons, AIS/flight caveats, and data gaps.
- Deepened terminal UX with workspace presets, provider health strip, status console, War Room right rail panel roster, layer-first UI payloads, and News/Screener/Crypto/Energy terminal upgrades.
- Added release archive hygiene regression test validating `.gitignore` inclusion and external/cache/generated/secrets exclusions.
- Added Goal 7 docs and expanded smoke imports for all new modules.

## Goal 6 Visual Intelligence Upgrade

- Added `pages/14_War_Room.py` with map-first global event view, layer controls, source freshness, right-side intelligence rail, country risk ranking, hotspot leaderboard, chokepoint cards, event timeline, market radar, and AI context.
- Added `pages/15_Financial_Terminal.py` with overview, statements, statistics, valuation, earnings, revenue, cash flow, balance sheet, segment/geography, and data-status tabs.
- Added War Room modules: `layer_registry`, `event_stream`, `geo_layers`, `intelligence_scoring`, `country_risk_model`, and `war_room`.
- Added Financial Terminal modules: `financial_terminal` and `financial_charts`, plus richer statement/ratio support in `fundamentals`.
- Added News to Market Impact modules: `news_asset_linker`, `market_impact_engine`, `catalyst_graph`, and `impact_visuals`.
- Upgraded News Intelligence with Market Impact and Catalyst Graph views backed by related-asset mapping and proxy/correlation context.
- Extended Scenario Engine with news-aware evidence integration.
- Added focused offline tests for Goal 6 modules and updated smoke imports.
- Added release packaging script that excludes external references, generated artifacts, caches, and secrets.

## Visual Command Terminal Upgrade

- Added terminal UI helpers, intelligence card builders, source freshness, market radar, signal fusion, hotspot scoring, event clustering, and news intelligence builders.
- Upgraded `app.py` with cross-asset metric deck, market radar, signal convergence, WorldMonitor-style maps, source freshness, and compact bottom snapshots.
- Upgraded News Intelligence into Command Feed, Market Impact, Geopolitical Map, Oil / Chokepoints, Crypto / Risk, Source Freshness, AI Brief, and WorldMonitor Adapter tabs.
- Upgraded Stock Analyzer with Terminal Overview, stronger financial/options visuals, and neutral event context.
- Upgraded Crypto Intelligence with derivatives radar, OI vs price, funding distribution, on-chain cards, and source freshness chart.
- Upgraded Screener with visual rank badges, result cards, session watchlist, heatmap, scatter, and source status.
- Added offline tests for terminal UI, news intelligence, signal fusion, hotspot scoring, event clustering, visual payload builders, map builders, and WorldMonitor runtime boundary checks.
- Added release hygiene report and expanded `.gitignore` for external reference code and generated artifacts.

## Phase 8-10 Session

- Finalized recovery governance with canonical source map, expectations manifest, recovery prevention policy, cleanup log, and guard tests.
- Restored public `pct_from_offset` helper in `lib/heatmaps.py`.
- Added safe generated-artifact cleanup script with dry-run default and source-file refusal.
- Added provider-agnostic AI layer for Anthropic, Gemini, Groq, OpenRouter, Ollama, and rule-based fallback.
- Added AI prompt templates, output safety filter, secret redaction, and neutral analysis functions.
- Upgraded `app.py` into the Overview Terminal.
- Added financial overview, options/gamma proxy, multi-asset screeners, bond/rate proxies, map visualization, and overview composition modules.
- Upgraded Market Pulse, Stock Analyzer, ETF Analyzer, Macro, News, Crypto Intelligence, Energy/Geopolitics, Scenario Lab, and Data Quality pages.
- Added Screener page.
- Added Phase 9 test coverage for AI providers, AI safety, AI analysis, fundamentals, options, screeners, maps, overview, WorldMonitor route paths, and regression guards.
- Added Phase 10 documentation and guides.

## Phase 5-7 Session

- Rebuilt core project scaffold after generated-artifact cleanup failure removed source files.
- Added equity breadth, diagnostics, options proxy, and neutral scenario matrices.
- Added EIA wrappers, energy fallback, oil-flow proxies, chokepoint registry, geopolitical news classification, and WorldMonitor adapter handling.
- Added Risk Lab metrics, stress tests, and cross-asset scenario routing.
- Added mocked tests and smoke checks.

## Goal 8 OpenBB Optional Backend

- Added optional OpenBB bridge, catalog, mapper, adapter, diagnostics, Data Hub page, optional requirements, and `.env.example`.
- Added OpenBB source modes to Financial Terminal, Portfolio Quant Lab, and Screener.
- Added Provider Center/Data Quality visibility for OpenBB install and optional keys.
- Added Strategy Research Engine v2 modules for candidate backtests, combinations, walk-forward/OOS validation, correlations, and report cards.
- Added mock-based tests that pass without OpenBB, internet, or API keys.

## Goal 9

- Added internal unified data layer, OpenBB-compatible endpoint catalog, native provider router, schema normalizers, freshness/gap engines, and facade.
- Added optional OpenBB endpoint resolver, real probes, runtime capability matrix, and MCP-ready endpoint manifest.
- Added macro/rates, energy/shipping/chokepoint, portfolio factor, Screener, Financial Terminal, War Room, Scenario Lab, and AI context integrations.
- Expanded smoke imports and added Goal 9 tests.

## Goal 10B

- Added modern visual system, visual tokens, summary keywords, click paths, command bar, shortcut help, refresh state, and source freshness indicators.
- Added internal heatmap tile/color/tooltip/drilldown/layout engines and optional TradingView supplement payloads.
- Added Relative Market Intelligence and Global Volatility Monitor.
- Added map-first OSINT payload modules, War Room live router, Energy map system, shipping/vessel truth labels, and News Intelligence Dashboard.
- Added split provider probe scripts and Provider Center split-script visibility.
- Added Goal 10B docs, smoke imports, and offline regression tests.

## Goal 11

- Added Personal Research Operating System workflow layer.
- Added local SQLite research workspace storage under `data/private/`.
- Added Research Workspace, Watchlist & Alerts, Report Inbox, and Strategy Decision Log pages.
- Added watchlist, alert, report, Strategy-as-Git, OSINT linking, command palette, quick action, and attachment modules.
- Added agent-skills-inspired spec/plan/test/review/security/ship governance reports.
- Expanded release hygiene exclusions for external references and private research data.

- Goal 11B: hardened Personal Research OS with enriched watchlist context, Alert Engine V2, deep reports, Strategy-as-Git V2, OSINT alias matching, provider/data snapshot memory, and deeper tests.

## Goal 11C Productization Update

Goal 11C adds product-quality Research OS UX: shared visual payloads, source freshness chips, command palette state, watchlist action cards/detail/event grid, report reader/review workflow, strategy review queue/artifact timeline, Intel Feed/Live Alerts/View Presets/Layer Panel, Research Tool Center, deeper tests, and release hygiene docs. External projects were inspected as conceptual references only; no external source code was copied or vendored.


## Goal 11D

- Completed external inventory for Kronos, QuantDinger, tensortrade, and worldview.
- Added shared command safety for palette and terminal router.
- Added explicit safe workflow actions with activity logging.
- Added stateful report reader and strategy review workflows.
- Connected Intel presets, time windows, layer metadata, locate payloads, and event actions.
- Added Research Tool Center actions and renderer helpers.
- Added Goal 11D tests and release hygiene checks.

## Goal 11E Update

Goal 11E: fixed command false positives, direct blocked workflow action behavior, Alert Engine V2 manual action wiring, energy report typing, Tool Center action coverage, selected-state persistence, and Markdown/HTML rendering safety.

## Goal 11F

- Restored `.env.example` in release packaging.
- Hardened command safety for advisory and guarantee phrasing while preserving descriptive research terms.
- Sanitized optional HTML report export.
- Routed Energy Brief command-palette actions to the Energy Brief workflow.
- Clarified release count terminology.

## Goal 12A

- Added local research-only option pricing models: Black-Scholes, Black-76, and Garman-Kohlhagen.
- Added Greeks, implied volatility solver, payoff templates, scenario grids, reports, attachments, provider caveats, Quant Model Snapshot Lab, Options Lab page, Tool Center actions, and command routes.

## Goal 12B Update — Options Chain, Vol Surface & Local Quant Diagnostics

Goal 12B adds supplied option-chain CSV ingestion, IV diagnostics, volatility-surface snapshots, advanced payoff templates, local option-book risk aggregation, contract-scaled Greeks, lightweight supplied-data quant diagnostics, and report/StrategyCommit-compatible research artifacts. All outputs remain research calculations only and do not provide investment advice, trading recommendations, hedging instructions, trade approvals, or execution instructions. External references remain excluded from runtime and release packages.



## Goal 12C Research Workflow Hardening


Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions.

Goal 12C hardens the supplied-data options workstation. It remains local-only, source-labeled, deterministic, and research-only.

Implemented areas:

- Time-to-expiry derivation from expiry and timestamp.
- Row-level model selection for equity/index, futures, FX, crypto-caveated, and unknown rows.
- Surface QA, no-arbitrage diagnostics, and surface diff payloads.
- Option-book stress using supplied positions and local repricing where available.
- Lightweight HRP/RMT/Kalman-lite/GARCH-lite/cointegration diagnostics without mandatory heavy runtimes.
- Report sanitizer for user-supplied identifiers, CSV formula text, and local path redaction.
- Explicit demo-mode boundary for Options Lab page payloads.


## Goal 12D

- Unified top command bar, terminal router, command palette, and workflow safety boundaries.
- Added price-based surface monotonicity, convexity, calendar, and parity residual diagnostics.
- Removed option-book 30-day fake TTE fallback.
- Added private options research case store and surface QA review queue.


## Goal 12E

- Added deterministic intel-feed regression coverage.
- Corrected option price convexity diagnostics.
- Added options case index/search.
- Added persistent surface review queue.
- Added Goal 13 action-less simulation prep.
