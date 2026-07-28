# Options Book Risk

Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions.

`lib/options_book_risk.py` aggregates user-supplied local positions by total Greeks, underlying, expiry, and moneyness bucket. It computes premium value, mark value, and unrealized PnL from supplied marks only. It does not output portfolio advice, hedge instructions, or rebalancing steps.


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
