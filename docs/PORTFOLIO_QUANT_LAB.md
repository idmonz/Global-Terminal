# Portfolio Quant Lab

The Portfolio Quant Lab is implemented in `pages/16_Portfolio_Quant_Lab.py` with supporting modules under `lib/`.

## Capabilities

- Editable Streamlit portfolio builder with add/remove rows through `st.data_editor`.
- Weight normalization, equal-weight research candidate generation, cash weight handling, and gitignored save/load storage.
- Historical buy-and-hold and rebalanced backtests with transaction cost and slippage estimates.
- Strategy candidate registry, alpha signal library, optimizer candidates, forecast lab, attribution reports, and stress-test integration.
- Dark Plotly visualizations for equity curves, drawdowns, heatmaps, rolling risk, allocation, contribution, correlation, turnover, and forward distributions.

## Storage

Saved portfolios use `data/private/portfolio.json` by default. The path is gitignored and excluded from release packages.

## Compliance

Backtests and model-estimated forward distributions are for research only. They are not financial advice, not predictions, and not recommendations. Past performance does not guarantee future results.

## Goal 8 OpenBB and Strategy Research Engine v2

- Portfolio Quant Lab supports source modes: Auto, Native only, OpenBB preferred, and OpenBB only.
- OpenBB price history is optional; native price history remains available.
- Strategy Research Engine v2 adds candidate backtests, alpha combinations, walk-forward/OOS diagnostics, strategy correlation, and report cards.
- Backtests and model-estimated forward distributions are for research only. They are not financial advice, not predictions, and not recommendations. Past performance does not guarantee future results.

## Goal 9 Factor Backend

Portfolio Quant Lab now includes a button-triggered factor backend selector. It reports factor coverage, source confidence, data quality penalty, strategy factor matrix, and factor data gaps.

Factors include technical, value, quality, growth, profitability, rates/macro, and options activity proxies.
# Goal 10 Update

Portfolio Quant Lab now includes explicit Goal 10 tabs:

- Alpha Combination Search
- Ensemble Builder
- Regime Performance
- Risk Budgeting
- Data Quality

The supporting modules are documented in `docs/ALPHA_STRATEGY_WORKBENCH.md`.

## Goal 11 Update

Goal 11 adds a local Personal Research Operating System layer. It stores private workspace state in SQLite under `data/private/`, adds watchlist/alerts/reports/strategy decision-log workflows, links OSINT/provider context to watchlist records, and remains manual, research-only, and release-hygiene controlled. No external source code, external folders, private DBs, secrets, live trading, broker execution, or background automation are included in release artifacts.
