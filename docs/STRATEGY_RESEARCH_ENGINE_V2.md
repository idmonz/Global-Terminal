# Strategy Research Engine v2

Goal 8 adds a neutral strategy research layer for Portfolio Quant Lab.

## Modules

- `strategy_backtest_engine`: candidate backtests, comparisons, leaderboard, risk-return table.
- `strategy_combination_engine`: alpha family combinations, ensemble returns, ensemble weights.
- `walk_forward_validator`: rolling train/test splits and walk-forward metrics.
- `oos_validation`: IS/OOS split, OOS metrics, decay comparison, overfit flags.
- `strategy_correlation`: return/drawdown correlation and cluster payloads.
- `strategy_report_cards`: summary, risk, data gap, and overfit cards.

Outputs are research candidates and backtest-ranked bundles, not advice.
