# Options Model Formulas

## Black-Scholes

European option with spot `S`, strike `K`, time `T`, rate `r`, carry/dividend yield `q`, and volatility `sigma`.

## Black-76

European futures option with futures price `F`, strike `K`, time `T`, rate `r`, and volatility `sigma`.

## Garman-Kohlhagen

FX option using domestic rate as discount rate and foreign rate as carry.

All formulas are implemented locally in `lib/options_pricing_models.py` and validated through deterministic tests.

Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions.

## Goal 12B Update — Options Chain, Vol Surface & Local Quant Diagnostics

Goal 12B adds supplied option-chain CSV ingestion, IV diagnostics, volatility-surface snapshots, advanced payoff templates, local option-book risk aggregation, contract-scaled Greeks, lightweight supplied-data quant diagnostics, and report/StrategyCommit-compatible research artifacts. All outputs remain research calculations only and do not provide investment advice, trading recommendations, hedging instructions, trade approvals, or execution instructions. External references remain excluded from runtime and release packages.

