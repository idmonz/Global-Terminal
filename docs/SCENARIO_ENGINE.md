# Scenario Engine

`lib/scenario_engine.py` routes scenario requests by asset type:

- Equity / Index / ETF: `lib.equity_scenarios`
- Crypto: `lib.crypto_scenarios`
- Energy / Oil: `lib.oil_flows`
- Portfolio / Basket: `lib.stress_tests`

Outputs normalize to:

- `asset_type`
- `asset`
- `horizon`
- `scenario`
- `evidence_weight`
- `evidence_summary`
- `triggers`
- `invalidation_level`
- `watch_points`
- `catalysts`
- `data_gaps`
- `confidence_caveat`
- `source_status`

Evidence weights are not prediction certainty.

Phase 8 AI summaries use `lib.ai_analysis.summarize_cross_asset_scenarios_neutral()` and are button-triggered from Scenario Lab. The AI layer receives compact scenario rows, source status, and data gaps rather than raw large dataframes.
## Goal 6 News-Aware Scenario Evidence

`lib/scenario_engine.py` now includes:

- `integrate_news_market_impact()`
- `add_news_impact_to_scenario_evidence()`
- `build_news_aware_scenario_matrix()`

These helpers attach news impact evidence, related assets, catalyst clusters, data gaps, and confidence caveats to scenario matrices. Evidence values are proxy/correlation context and do not alter the existing canonical scenario columns or routing behavior.
