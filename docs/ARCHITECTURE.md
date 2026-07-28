# Architecture

The terminal is a Python/Streamlit app with small library modules under `lib/` and pages under `pages/`.

## Core Systems

- `lib/data_status.py`: `DataResult` source, freshness, cache, estimate, and missing-data metadata.
- `lib/cache.py`: JSON and in-memory cache helpers.
- `lib/compliance.py`: baseline disclosure and neutral-language sanitization.
- `lib/ai_safety.py`: Phase 8 AI output filtering, disclosure, and secret redaction.
- `lib/ai_providers.py`: provider-agnostic AI adapters and rule-based fallback.
- `lib/ai_analysis.py`: button-triggered neutral analysis entry points.

## Market Systems

- goal1: `lib/market_data.py`, `lib/global_markets.py`, `lib/heatmaps.py`, and static universe CSVs.
- Phase4: `lib/crypto_prices.py`, `lib/crypto_derivatives.py`, `lib/crypto_onchain.py`, `lib/crypto_scenarios.py`, and Crypto Intelligence page.
- goal3: `lib/equity_breadth.py`, `lib/equity_scenarios.py`, `lib/energy_data.py`, `lib/oil_flows.py`, `lib/geopolitical_news.py`, `lib/worldmonitor_adapter.py`, `lib/risk.py`, `lib/stress_tests.py`, and `lib/scenario_engine.py`.

## Goal 7 Systems

- Portfolio Quant Lab: `portfolio_state`, `portfolio_backtester`, `portfolio_optimizer`, `alpha_library`, `strategy_registry`, `factor_engine`, `return_forecast`, `performance_attribution`, `portfolio_visuals`, and `portfolio_quant_lab`.
- Live Data Provider Center: `provider_registry`, `provider_diagnostics`, `live_feeds`, and `realtime_connectors`.
- Terminal UX: `terminal_ui` workspace/provider/layer/right-rail payload helpers plus layer UI payloads in `layer_registry`.

## Phase 8 Additions

- `lib/overview.py`: Overview Terminal data composition.
- `lib/map_viz.py`: event, chokepoint, country-risk, route-proxy, and region maps.
- `lib/fundamentals.py`: financial overview normalization and metrics.
- `lib/options_flow.py`: option-chain ratios and gamma proxy.
- `lib/screeners.py`: multi-asset screener builders.
- `lib/bond_data.py`: bond/rate proxy universe and metrics.

External data functions degrade gracefully and label estimates or missing keys.

## Goal 8 OpenBB Optional Backend

- `lib/openbb_bridge.py`: lazy import, optional status, DataResult-compatible OpenBB calls.
- `lib/openbb_catalog.py`: local metadata catalog for OpenBB target domains and app mappings.
- `lib/openbb_data_mapper.py`: schema mappers that keep missing values as data gaps.
- `lib/openbb_provider_adapter.py`: high-level optional adapter functions for financials, ETFs, options, macro, commodities, technicals, and screeners.
- `lib/openbb_diagnostics.py`: install/key/catalog diagnostics for Provider Center and OpenBB Data Hub.
- `lib/openbb_screener_backend.py`: optional stock/ETF screener merge layer.
- Strategy Research Engine v2 lives in `strategy_backtest_engine`, `strategy_combination_engine`, `walk_forward_validator`, `oos_validation`, `strategy_correlation`, and `strategy_report_cards`.

## Goal 9 Unified Data Layer

Goal 9 adds `data_contracts`, `endpoint_catalog`, `provider_router`, `schema_normalizer`, `data_router`, `unified_data_layer`, `data_freshness_engine`, and `data_gap_engine`.

The app now has a native-first route from user request to `UnifiedDataResult`, with optional OpenBB bridge/probe support and explicit source confidence, freshness, caveats, proxy labels, and data gaps.

## Goal 10 Productization Layer

- Executive UX: `executive_summary_engine`, `terminal_workspace_router`, `drilldown_recommendation_engine`, `market_briefing_cards`, `terminal_briefing_payloads`, and `cross_asset_regime_summary`.
- Command UX: `terminal_function_registry`, `terminal_command_router`, `command_history`, `intel_scorecard_engine`, and `security_signal_rules`.
- Provider probe/free data: `provider_probe_runner`, `provider_probe_store`, `provider_probe_visuals`, `provider_health_engine`, `no_key_provider_catalog`, and project-native free/no-key provider adapters.
- Environment: `env_loader` loads `.env` safely and exposes masked key status.
- Strategy workbench: `alpha_combination_search`, `strategy_ensemble_engine`, `regime_performance_engine`, `strategy_walk_forward_report`, `strategy_risk_budgeting`, `strategy_visual_lab`, and `strategy_data_quality`.

## Goal 10B Visual Terminal Layer

- Visual system: `visual_tokens`, `modern_visual_system`, `summary_keyword_engine`, `click_path_engine`, `ui_action_cards`, `top_command_bar`, `shortcut_registry`, `shortcut_help`, `refresh_state`, and `source_freshness_indicator`.
- Heatmaps: `heatmap_tile_engine`, `heatmap_color_scales`, `heatmap_tooltip_engine`, `heatmap_visual_theme`, `heatmap_drilldown_engine`, `heatmap_layout_engine`, `market_overview_layout`, and `tradingview_widget_embed`.
- Market intelligence: `relative_market_intelligence` and `global_volatility_monitor`.
- Map-first OSINT: `world_event_geocoder`, `live_news_event_pipeline`, `osint_map_layers`, `map_event_clusterer`, `map_marker_engine`, `geospatial_tooltip_engine`, `war_room_live_data_router`, `war_room_timeline_engine`, `shipping_map_layers`, `vessel_data_router`, `energy_geopolitics_map`, and `news_intelligence_dashboard`.
- Provider diagnostics: split scripts under `scripts/probe_*.py` with `run_provider_probes.py --suite` wrapper support.

## Goal 11 Update

Goal 11 adds a local Personal Research Operating System layer. It stores private workspace state in SQLite under `data/private/`, adds watchlist/alerts/reports/strategy decision-log workflows, links OSINT/provider context to watchlist records, and remains manual, research-only, and release-hygiene controlled. No external source code, external folders, private DBs, secrets, live trading, broker execution, or background automation are included in release artifacts.


## Goal 11B Research OS Layer

The Research OS layer stores private workflow state in SQLite and consumes existing Goal 10B data/provider/OSINT modules through optional adapters. It does not replace the Unified Data Layer.

## Goal 11C Productization Update

Goal 11C adds product-quality Research OS UX: shared visual payloads, source freshness chips, command palette state, watchlist action cards/detail/event grid, report reader/review workflow, strategy review queue/artifact timeline, Intel Feed/Live Alerts/View Presets/Layer Panel, Research Tool Center, deeper tests, and release hygiene docs. External projects were inspected as conceptual references only; no external source code was copied or vendored.


## Goal 11D Interaction Layer

Goal 11D introduces `research_command_safety`, `research_workflow_actions`, report/strategy selection workflow modules, Intel workflow filters, tool actions, and Streamlit renderer helpers. These modules sit above the existing SQLite stores and below Streamlit pages, preserving Goal 10B/11/11B/11C engines.

## Goal 11E Update

Goal 11E architecture note: command safety is shared by palette/router/direct workflow actions; Research OS state uses import-safe session helpers; manual alert evaluation calls Alert Engine V2 only with supplied context.

## Goal 11F architecture note

Goal 11F keeps the Research OS architecture additive: shared command safety, safe workflow actions, report-export sanitization, and release setup artifacts remain Python/Streamlit/SQLite only.

## Goal 12A Options / Quant Model Layer

Goal 12A adds `options_*` modules for local option calculations and `quant_model_*` modules for model snapshot artifacts. The layer sits above validation and below Report Inbox, Strategy-as-Git, Research Tool Center, Command Palette, and the new Options Lab page.

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


## Goal 12D Architecture Addition

Options workflows now include a private research case store under `data/private/options_cases/`, a surface QA review queue, price-based surface diagnostics, and unified command safety through `research_command_safety.py`.


## Goal 12E Architecture Update

Options research cases now have a private searchable index and persistent surface QA review queue. Low-level intel feed construction is deterministic by default.
