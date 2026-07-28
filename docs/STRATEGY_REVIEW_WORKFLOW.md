# Strategy Review Workflow

Strategy-as-Git now includes review queue, commit reader, guard dashboard, graph table, diff panel, artifact timeline, forward tracking panel, linked reports/watchlist context, and review actions.

It remains a research record workflow only.


## Goal 11D selected-review state

Strategy-as-Git now supports selected commit state, selected reader payloads, parent/child diff payloads, selected guard dashboard, review status updates, artifact attachment, and artifact timeline refresh.

## Goal 11E Update

Goal 11E update: selected strategy commit state persists through review updates and last action result is recorded in session state.

## Goal 12A artifact integration

Strategy-as-Git commits can store options result snapshots and quant model snapshots as review artifacts. These artifacts are research records only.

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


## Goal 12D Options Case Linkage

Surface review items and options case artifacts can be linked to research reports and Strategy-as-Git review records as audit artifacts only.
