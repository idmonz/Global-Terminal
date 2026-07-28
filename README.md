# Global Market Analyst Terminal

Educational Streamlit dashboard for cross-asset market diagnostics, neutral scenario analysis, AI-assisted research summaries, and portfolio risk context.

## Run

```powershell
streamlit run app.py
```

The base app launches without API keys. Optional keys enable richer feeds and AI providers:

- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `OPENROUTER_API_KEY`
- `OLLAMA_BASE_URL=http://localhost:11434/v1`
- `EIA_API_KEY`
- `WORLD_MONITOR_BASE_URL`
- `WORLD_MONITOR_KEY`

## Current Coverage

- Goal 7 Portfolio Quant Lab with editable portfolios, gitignored save/load, backtests, strategy candidates, alpha signals, optimizer candidates, model-estimated forward distributions, attribution, stress integration, and data status.
- Goal 7 Data Provider Center with provider registry, optional-key diagnostics, live-feed readiness, AIS/flight caveats, data gaps, and setup guidance.
- Goal 10 executive productization layer with Overview executive brief, provider quality scorecards, OpenBB probe quality summaries, and Alpha Strategy Workbench.
- Goal 7 terminal shell deepening with workspace presets, provider health strip, status console, richer War Room right rail, layer-first UI payloads, and terminalized News/Screener/Crypto/Energy surfaces.
- Map-first Global War Room with event map, layer registry, static chokepoints, route exposure proxies, source freshness, country risk heuristics, hotspot leaderboard, and right-side intelligence rail.
- Financial Terminal with reported statements, ratio/statistics panels, valuation context, earnings gaps, revenue/cash-flow/balance-sheet tabs, and data availability matrix.
- News to Market Impact Engine with related asset mapping, potential market channels, observed proxy reaction tables, catalyst graph, scenario evidence contribution, and caveats.
- Overview Terminal with cross-asset cards, chart modes, market radar, signal convergence, heatmap strip, mini-panels, event maps, source freshness, and button-triggered neutral AI brief.
- Terminal UI design system with compact cards, severity badges, freshness badges, data-gap badges, mini bars, and sparklines.
- News Intelligence command feed with market-impact matrix, geopolitical map, chokepoint map, crypto/risk feed, source freshness, AI brief, and WorldMonitor adapter tab.
- Global heatmaps for US sectors, S&P 500 seed, Nasdaq 100 seed, Korea watchlist, G7, crypto, and cross-asset proxies.
- Crypto Intelligence with Binance/CoinGecko/DefiLlama public paths, derivatives radar, OI/price view, funding distribution, estimated liquidation pressure map, and scenario monitor.
- Equity diagnostics, terminal overview, financial overview, valuation cards, options/gamma proxy, scenario matrix, and neutral AI research note.
- Energy and geopolitics panels for EIA optional fundamentals, yfinance fallback, chokepoints, route proxy maps, news, WorldMonitor adapter, and scenarios.
- Risk Lab, Scenario Lab, Data Quality, and visual multi-asset Screener with rank badges and session watchlist.

## Free-Mode Behavior

- Rule-based AI fallback requires no paid provider.
- Missing keys return source-status warnings rather than crashes.
- Estimated/proxy fields are labeled.
- No fake live data is presented as real.
- WorldMonitor source under `external/` is reference-only and ignored.
- War Room route arcs and chokepoints are proxy/static layers, not live vessel traffic.
- Financial segment/geographic revenue and forecast fields remain data gaps unless real provider fields exist.
- News impact outputs use proxy/correlation language and do not claim causality.
- AI calls are button-triggered and output is filtered for neutral research language.

## Tests

```powershell
python scripts/run_smoke_tests.py
python -m pytest -q
```

## Key Docs

- `docs/AI_PROVIDER_GUIDE.md`
- `docs/GOAL_6_FINAL_REPORT.md`
- `docs/WAR_ROOM_SYSTEM.md`
- `docs/FINANCIAL_TERMINAL_GUIDE.md`
- `docs/NEWS_MARKET_IMPACT_ENGINE.md`
- `docs/CATALYST_GRAPH_SYSTEM.md`
- `docs/MARKET_IMPACT_CAVEATS.md`
- `docs/WORLDMONITOR_INTEGRATION_GUIDE.md`
- `docs/TERMINAL_UI_DESIGN_SYSTEM.md`
- `docs/NEWS_INTELLIGENCE_SYSTEM.md`
- `docs/MARKET_RADAR_SYSTEM.md`
- `docs/SIGNAL_FUSION_SYSTEM.md`
- `docs/HOTSPOT_SCORING_CAVEATS.md`
- `docs/FINANCIAL_OVERVIEW_GUIDE.md`
- `docs/SCREENER_GUIDE.md`
- `docs/OPTIONS_GAMMA_PROXY_CAVEATS.md`
- `docs/PHASE_10_FINAL_BUILD_REPORT.md`
- `docs/GOAL_10_PRODUCTIZATION_REPORT.md`

## Goal 8 OpenBB Optional Backend

- OpenBB is available as an optional backend bridge through `requirements-openbb.txt`.
- Base launch still works without OpenBB installed and without paid API keys.
- New page: `pages/18_OpenBB_Data_Hub.py`.
- Financial Terminal, Portfolio Quant Lab, and Screener expose source modes where OpenBB can be preferred or isolated.
- OpenBB source code is not vendored into runtime modules or release packages.
- See `docs/OPENBB_OPTIONAL_BACKEND_BRIDGE.md`, `docs/OPENBB_LICENSE_BOUNDARY.md`, and `docs/OPENBB_SETUP_GUIDE.md`.

## Goal 9 Unified Data Layer

- Added a native unified data layer with contracts, endpoint catalog, provider router, schema normalization, freshness, data gaps, and a facade.
- Added optional OpenBB endpoint resolver, real probes, and runtime capability matrix.
- Added macro/rates, energy/shipping/chokepoint, portfolio factor, Screener, Financial Terminal, and AI/MCP preparation integrations.
- OpenBB remains optional; base launch works without OpenBB installed or paid provider keys.

## Goal 10 Productization Layer

- Added an executive brief to the Overview Terminal for cross-asset state, source quality, data gaps, largest tape moves, and connected workflows.
- Added provider quality scoring to Data Quality, Data Provider Center, and OpenBB Data Hub.
- Added Alpha Strategy Workbench inside Portfolio Quant Lab for ranked historical candidates, validation checks, ensemble research, combinations, and factor/source quality context.
- No MCP/API server surface is started in Goal 10; optional backend probes remain button-triggered.
- Added Goal 10 command UX (`CC`, `HELP`, `DATA PROBE`, `AAPL FA`, `BTC CRYPTO`, `SPY PORT`) and dry-run provider probes.
- Added safe `.env` loading via `lib/env_loader.py`; `.env.example` remains blank-only and release-safe.
- See `docs/GOAL_10_FINAL_REPORT.md`, `docs/ENVIRONMENT_VARIABLE_SETUP.md`, `docs/PROVIDER_PROBE_SYSTEM.md`, and `docs/ALPHA_STRATEGY_WORKBENCH.md`.

## Goal 10B Visual Terminal Hardening

- Added a modern visual system with tokens, keyword chips, click-next cards, top command bar payloads, shortcut help, refresh state, and source freshness indicators.
- Added project-native heatmap engines for market, crypto, portfolio, provider health, source freshness, War Room, and Energy risk views.
- Added Relative Market Intelligence and Global Volatility Monitor payloads to the Overview Terminal.
- Upgraded War Room, Energy Geopolitics, News, Provider Center, Crypto Intelligence, Screener, Financial Terminal, and Portfolio Quant Lab with Goal 10B summary-first/map-first payloads.
- Split provider probes into OpenBB runtime, provider matrix, macro/energy, crypto, and news/OSINT scripts.
- See `docs/GOAL_10B_FINAL_REPORT.md`, `docs/HEATMAP_VISUALIZATION_SYSTEM.md`, `docs/MAP_FIRST_OSINT_PIPELINE.md`, and `docs/PROVIDER_PROBE_SCRIPT_SPLIT.md`.

## Goal 11 — Personal Research Operating System

Goal 11 adds local research workflow pages and modules: Research Workspace, Watchlist & Alerts, Report Inbox, and Strategy Decision Log. The system is manual/button-triggered, stores private state under `data/private/`, excludes private/external artifacts from release, and is for research and monitoring only. It does not provide financial advice, trading recommendations, or execution instructions.


## Goal 11B Personal Research OS

Goal 11B adds operational hardening for the local research workspace: enriched watchlists, stateful manual alerts, type-specific reports, Strategy-as-Git guard checks, OSINT alias matching, provider/data-quality memory, and overview navigation.

## Goal 11C Productization Update

Goal 11C adds product-quality Research OS UX: shared visual payloads, source freshness chips, command palette state, watchlist action cards/detail/event grid, report reader/review workflow, strategy review queue/artifact timeline, Intel Feed/Live Alerts/View Presets/Layer Panel, Research Tool Center, deeper tests, and release hygiene docs. External projects were inspected as conceptual references only; no external source code was copied or vendored.

## Goal 11D Research OS interaction hardening

Goal 11D adds shared command safety, explicit manual workflow actions, selected report/strategy review loops, Intel preset/time/layer workflow connection, Research Tool Center actions, and import-safe Streamlit renderer helpers. The workspace remains research-only and does not add external runtime dependencies.

## Goal 11E Update

Goal 11E adds pre-Goal12 micro-hardening for command safety, workflow actions, Alert Engine V2 manual evaluation, selected-state persistence, Tool Center action coverage, and safe Markdown rendering.

## Goal 11F hotfix

Goal 11F restores the placeholder-only `.env.example`, hardens command safety, sanitizes optional HTML report export, fixes Energy Brief routing, and clarifies release package count terminology. The workspace remains research-only.

## Goal 12A — Options Pricing & Quant Model Lab

Goal 12A adds a research-only Options Pricing & Quant Model Lab with local Black-Scholes, Black-76, Garman-Kohlhagen, Greeks, implied volatility, payoff/scenario analysis, provider caveats, Report Inbox attachments, Strategy-as-Git artifacts, and Quant Model Snapshot infrastructure. No live trading, broker route, external model runtime, or mandatory paid provider dependency was added.

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


## Goal 12D Update

Added unified command safety, price-based options surface QA, no-fake-TTE option-book stress, unknown-model manual-mode handling, private options research case store, and surface QA review queue.


## Goal 12E

Goal 12E adds deterministic regression gates, a private options case index, persistent surface review queue, Options Lab case/review payloads, and Goal 13 action-less simulation preparation.
