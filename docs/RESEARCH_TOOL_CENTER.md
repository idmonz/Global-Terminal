# Research Tool Center

The Research Tool Center is a manual tool hub with Data Provider Tools, Watchlist Tools, Report Tools, Strategy Review Tools, OSINT Tools, Export/Backup Tools, and Diagnostics Tools.

Every card includes tool name, purpose, command, page, data required, output type, caveat, and research_only flag.


## Goal 11D tool actions

Research Tool Center cards can map to safe manual workflow actions. Tool searches, missing-data caveats, and action result payloads are handled by `lib/research_tool_actions.py`.

## Goal 11E Update

Goal 11E update: Tool Center cards now map to safe manual workflow actions such as provider dry-run, data-quality inspection, view-preset inspection, and release-hygiene inspection.

## Goal 11F note

Tool Center remains manual and research-only. Setup guidance now includes the release-included `.env.example` provider template.

## Goal 12A tools

The Tool Center now exposes Price Option, Solve Implied Volatility, Build Payoff Scenario, Generate Options Report, Attach Options Result to Strategy Commit, Create Quant Model Snapshot, Attach Model Snapshot to Report, and Inspect Options Provider Capability.

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


## Goal 12D Tools

Added Create Options Research Case, Save Surface QA to Review Queue, and Save Option Book Stress to Case tools.
