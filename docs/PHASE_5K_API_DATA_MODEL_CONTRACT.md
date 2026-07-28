# Phase 5K API And Data Model Contract

Updated: 2026-06-21

## Additive Boundary

- Payload type: `portfolio_risk`
- Domain version: `portfolio_risk.v1`
- Route: `GET /api/portfolio-risk`
- Fixture: `static/api-fixtures/portfolio-risk.json`
- Existing envelope version remains `phase_2b.v1`.

Query parameters are limited to safe state: `portfolio`, `period`, `benchmark`, and `include_runtime`.

## Pipeline

1. holdings ingestion and strict normalization;
2. symbol-only provider request;
3. price/history normalization;
4. valuation and allocation;
5. complete-overlap return alignment;
6. performance and drawdown;
7. risk and pairwise correlation;
8. factor and attribution models;
9. historical replay and deterministic hypothetical stress;
10. JSON-safe presentation contract.

No DataFrame, Series, datetime object, Plotly object, Streamlit object, local path, or secret crosses the API boundary.

## Top-Level Domain Shape

- `portfolio_risk_version`
- `portfolio`
- `holdings`
- `allocation`
- `performance`
- `risk`
- `correlation`
- `factors`
- `attribution`
- `stress_tests`
- `source_register`
- `data_gaps`
- `privacy`
- `readiness`
- `summary`
- `disclosure`

## Quant Semantics

- Valuation is `quantity * observed_price`; cash is explicitly modeled at 1 base-currency unit.
- Simple cumulative return and time-weighted return are both exposed only because the demo has no external cash flows. Money-weighted return is unavailable without dated cash flows.
- Daily returns use `pct_change(fill_method=None)`.
- Portfolio history uses a declared complete overlap across included history assets; no missing return is set to zero. Cash return is the only explicit zero series.
- Annualization is 252 observations and stated in each affected metric.
- VaR/CVaR are historical daily 95% estimates, not loss forecasts.
- Correlation is Pearson on pairwise complete overlap and includes pair sample counts.
- Factor results use named public proxy returns and expose beta, alpha, R-squared, model sample count, residual return and unexplained share.
- Return attribution exposes arithmetic contribution and a residual so the reported total reconciles.
- Risk contribution uses the complete-overlap covariance matrix and must sum to one within tolerance when portfolio variance is positive.
- Stress rows are typed as `historical_replay` or `deterministic_hypothetical`; shocks and coverage are explicit.

## Runtime Policy

- Free-first provider: yfinance delayed public history.
- Cache TTL: 5 minutes.
- Stale fallback: 30 minutes.
- Per-key single-flight lock.
- Fixture mode is deterministic and network-free.
- Runtime failure cannot mutate fixture rows into live rows.

## Minimum Gates

- Performance/risk: at least 40 complete daily observations.
- Rolling series: at least 63 complete daily observations.
- Correlation: at least 20 pairwise observations.
- Factor regression: at least 40 complete observations.
- Historical worst-window stress: at least the requested window plus one observation.

## Provenance

Every holding or major result group carries, where applicable:

`provider`, `source_url`, `fetched_at`, `freshness`, `source_status`, `confidence`, `sample_count`, `window`, `units`, `caveat`, `data_gap`, and `not_financial_advice=true`.

