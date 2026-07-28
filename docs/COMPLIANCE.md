# Compliance

The app is educational and informational only. Scenario outputs use evidence weights, uncertainty, source status, and watch-points instead of trading instructions.

## Controls

- The disclosure footer is rendered from `lib/config.py`.
- Existing scenario and table text is sanitized through `lib/compliance.py` where needed.
- AI output is filtered through `lib/ai_safety.py`.
- AI prompt templates state that the model must not personalize advice or issue trading instructions.
- Prompt context shown in the UI is redacted.
- AI calls are button-triggered only.
- Goal 7 portfolio, strategy, optimizer, and forecast outputs are labeled as research candidates, scenario estimates, or model-estimated distributions.
- Provider Center exposes optional missing keys and unavailable feeds without fabricating data.

## Data Labeling

- Estimated/proxy data is labeled.
- Gamma exposure is labeled as an estimate, not dealer-confirmed GEX.
- Route maps do not claim live AIS vessel flow.
- AIS and flight surfaces explicitly state unavailable status unless optional providers are configured and tested.
- Missing providers are displayed as data gaps.
- News severity, region, impact channel, and credibility classification is heuristic.
- Portfolio backtests and forward distributions include research-only caveats and do not guarantee future results.
- Market radar, signal fusion, and hotspot scores are labeled as heuristic or estimated.
- WorldMonitor is reference-only unless an explicit adapter endpoint is configured.

## Visual Terminal Controls

- Terminal cards use neutral labels such as Constructive backdrop, Mixed evidence, Deteriorating breadth, Elevated volatility, Crowding risk, Liquidity pressure, Source stale, and Data gap.
- Source freshness badges distinguish fresh, stale, missing, error, and estimated states.
- AI brief panels are button-triggered and keep uncertainty, watch-points, and data gaps visible.
## Goal 6 Compliance Notes

- War Room outputs label country risk and hotspot scores as heuristic.
- Chokepoint and route layers are static/proxy layers and explicitly state no live vessel traffic.
- Financial Terminal forecast, segment, and geography panels show data gaps unless real provider fields exist.
- News impact outputs use neutral terms such as observed related market move, potential channel, proxy reaction, correlation context, and data gap.
- AI context includes AI summary framing, primary-data verification, not-financial-advice language, uncertainty, and data gaps.

## Goal 8 OpenBB Compliance Notes

- OpenBB is optional and not required for base launch.
- Provider availability, licensing, data rights, and API key requirements must be verified by the user before production or commercial use.
- OpenBB-enriched AI context is compact and source-labeled; raw massive DataFrames are not sent to AI helpers.
- Portfolio/strategy pages retain the research-only disclosure for backtests and model-estimated forward distributions.
- Missing OpenBB, missing keys, and paid-provider gaps are shown as data gaps rather than inferred values.

## Goal 9 Compliance Notes

`UnifiedDataResult` carries caveats, proxy flags, data gaps, source confidence, and freshness into UI and AI context packets.

OpenBB remains optional. Provider availability, licensing, data rights, and key requirements must be verified by the user before production or commercial use.
# Goal 10 Update

Goal 10 preserves the educational/research-only boundary. Command routing never executes broker/order actions. Provider probes are diagnostics only. Strategy workbench outputs are research candidates with source confidence, proxy labels, data quality, sample period, and caveats.

Backtests and model-estimated forward distributions are for research only. They are not financial advice, not predictions, and not recommendations. Past performance does not guarantee future results.

## Goal 10B Compliance Notes

- The visual terminal remains research-only and does not execute trades.
- Command UX validates and blocks trade-execution language.
- Heatmap, RMI, volatility, OSINT, Energy, News, and provider probe payloads include source freshness, confidence, proxy/missing/historical-only labels, or caveats.
- No external source tree is copied into runtime modules.
- No fake live AIS, flight, NASA FIRMS, liquidation heatmap, official news feed, or provider data is presented.

## Goal 11 Update

Goal 11 adds a local Personal Research Operating System layer. It stores private workspace state in SQLite under `data/private/`, adds watchlist/alerts/reports/strategy decision-log workflows, links OSINT/provider context to watchlist records, and remains manual, research-only, and release-hygiene controlled. No external source code, external folders, private DBs, secrets, live trading, broker execution, or background automation are included in release artifacts.


## Goal 11B compliance

Goal 11B remains research-only. It adds no broker execution, order routing, automatic rebalancing, email auto-send, or background daemon.

## Goal 11C Productization Update

Goal 11C adds product-quality Research OS UX: shared visual payloads, source freshness chips, command palette state, watchlist action cards/detail/event grid, report reader/review workflow, strategy review queue/artifact timeline, Intel Feed/Live Alerts/View Presets/Layer Panel, Research Tool Center, deeper tests, and release hygiene docs. External projects were inspected as conceptual references only; no external source code was copied or vendored.


## Goal 11D compliance update

Goal 11D blocks market-action and broker-like command intent in both command palette and terminal router while allowing non-actionable market-structure research phrases. Workflow actions are manual, local, source-labeled, and research-only.

## Goal 11E Update

Goal 11E compliance note: descriptive market-structure and macro-duration research phrases are allowed, while market-action intent remains blocked across command palette, terminal router, and direct workflow actions.

## Goal 11F compliance update

Command Palette, Terminal Router, and workflow actions use the same research-only command boundary. Optional report HTML is escaped by default. `.env.example` is allowed in release only as a blank setup template.

## Goal 12A compliance update

Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions. Goal 12A uses supplied/local data by default, includes provider caveats, and adds no broker/order pathway, autonomous action system, or external model runtime.

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


## Goal 12D Compliance Boundary

All new options case, surface review, surface QA, option-book stress, and diagnostics workflows are research-only and do not provide investment advice, trade approvals, hedging instructions, or execution instructions.


## Goal 12E Boundary

Case indexing and review persistence are research artifacts only. They are not approvals, hedging instructions, execution instructions, or automated market actions.
