# Options Payoff and Scenarios

Implemented modules:

- `lib/options_payoff.py`
- `lib/options_strategy_templates.py`
- `lib/options_scenarios.py`

Supported mathematical profiles: single option, covered call profile, protective put profile, vertical spread, straddle, and strangle. Scenario grids cover price shocks, volatility shocks, time decay, rates, PnL from supplied premium, and Greeks.

Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions.

## Goal 12B Update — Options Chain, Vol Surface & Local Quant Diagnostics

Goal 12B adds supplied option-chain CSV ingestion, IV diagnostics, volatility-surface snapshots, advanced payoff templates, local option-book risk aggregation, contract-scaled Greeks, lightweight supplied-data quant diagnostics, and report/StrategyCommit-compatible research artifacts. All outputs remain research calculations only and do not provide investment advice, trading recommendations, hedging instructions, trade approvals, or execution instructions. External references remain excluded from runtime and release packages.

