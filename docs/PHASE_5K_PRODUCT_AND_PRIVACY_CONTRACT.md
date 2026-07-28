# Phase 5K Product And Privacy Contract

Updated: 2026-06-21

## Product Outcome

`/?view=portfolio-risk` is a product-first, research-only Portfolio And Risk Workstation. A user can complete one coherent journey from a deterministic fictional portfolio to valuation, allocation, performance, drawdown, risk, correlation, factor, attribution, and stress evidence.

The phase is not a broker portfolio, execution surface, recommendation engine, or hosted account service.

## Canonical Route

`/?view=portfolio-risk&portfolio=demo-core&surface=overview&period=1y&benchmark=SPY&mode=live-if-available`

Allowed URL state:

- safe portfolio alias;
- analysis surface;
- period;
- benchmark symbol;
- runtime mode.

Forbidden URL state:

- quantities, cost bases, market values;
- account, broker, tax, identity, or personal labels;
- raw local file paths or database identifiers.

## Required Product Surfaces

1. First viewport: value, valuation coverage, as-of state, allocation, performance/drawdown, risk metrics, and visible gaps.
2. Holdings: dense valuation table, missing-price handling, source state, and symbol drilldown.
3. Performance: portfolio and benchmark normalized series, drawdown, method/window/sample labels.
4. Risk: annualized volatility, downside volatility, VaR/CVaR, beta, max drawdown, concentration, and risk contribution.
5. Correlation: source-aligned matrix plus pairwise overlap counts.
6. Factors: proxy model exposures, model fit, source, residual, and unexplained share.
7. Attribution: arithmetic return contribution, risk contribution, residual, and reconciliation.
8. Stress: observed worst-window replay and deterministic hypothetical shocks with assumptions.
9. Truth rail: provider, retrieval time, freshness, coverage, privacy class, caveats, gaps, and no-advice disclosure.

## Privacy Classes

### Deterministic demo

- Fictional quantities and cost bases authored for regression and product demonstration.
- May enter static fixtures and release screenshots.
- Must be labeled `deterministic_fictional_demo`, `fixture`, and `release_safe=true`.

### Local private

- User-supplied holdings resolved only from approved private local storage or an explicit local request body.
- Must never enter static fixtures, source control, query strings, release screenshots, release ZIPs, telemetry, external AI/search, or provider calls beyond the minimum required symbols.
- Provider requests may include symbols only; quantity, cost, account and note fields are never sent.

## Failure Semantics

- Missing price: current price and market value remain null; the holding is excluded from known-value totals and coverage is reduced.
- Missing history: the asset is excluded from return calculations and history coverage is reduced.
- Missing observation: never converted to zero. Portfolio return calculations use a declared complete overlap window.
- Insufficient samples: chart/model panel is unavailable with a concrete minimum and observed count.
- Provider failure: stale cache may be used within policy and labeled stale; otherwise no live performance is claimed.
- Malformed/duplicate/negative holdings: rejected with field-level reasons, never silently repaired into a position.
- Non-USD position without FX: valuation remains unavailable; no implicit 1:1 conversion.

## Research Boundary

All outputs are descriptive historical or assumption-bound calculations. The product must not emit recommended weights, rebalance instructions, position sizing, entry/exit levels, hedging instructions, trade approvals, broker actions, autonomous actions, or execution controls.

