# Phase 5K Web Implementation Report

Updated: 2026-06-21

## Delivered Journey

`/?view=portfolio-risk&portfolio=demo-core&surface=overview&period=1y&benchmark=SPY&mode=live-if-available`

The route is now a product-first Portfolio And Risk Workstation instead of falling through to Market contract diagnostics.

Delivered surfaces:

- valuation and holdings coverage;
- asset-class/sector/currency allocation;
- portfolio/benchmark performance and drawdown;
- annualized risk, daily historical VaR/CVaR, beta and concentration;
- Pearson correlation with pairwise sample counts;
- public-proxy OLS factors with residual and unexplained share;
- arithmetic return and covariance risk attribution with reconciliation residual;
- observed worst-window replay and deterministic hypothetical stress;
- compact provider/privacy rail and no-advice boundary;
- AAPL and BTC holding drilldown to verified symbol workstations.

## Runtime Composition

- New domain engine: `lib/portfolio_risk_workstation.py`.
- New additive payload: `portfolio_risk.v1` inside `phase_2b.v1`.
- New route: `GET /api/portfolio-risk`.
- New deterministic fixture: `static/api-fixtures/portfolio-risk.json`.
- New web component: `PortfolioRiskWorkstation.tsx`.
- Product navigation now exposes Portfolio as a first-class workspace.

## Data And Model Boundary

- Free delayed yfinance history is requested with symbols only.
- Five-minute TTL, per-key single-flight lock, and 30-minute stale fallback are implemented.
- Quantity, cost basis, names and notes are not sent to providers.
- Missing prices remain null; missing returns are never converted to zero.
- Complete overlap is required for portfolio performance and covariance calculations.
- Cash return is the only explicitly defined zero series.
- Money-weighted return remains unavailable without dated cash flows.
- Research snapshot metadata runs through the existing guard pipeline without holdings, quantities or cost basis.

## Honest Gaps

- The web currently ships the fictional demo journey; arbitrary local holding entry/import is not yet a hosted/user-account workflow.
- yfinance is unofficial and delayed.
- USD is the only valued currency without an FX adapter.
- Factor proxies are public asset returns, not licensed institutional factors.
- No tax lots, corporate-action ledger, dated cash-flow IRR, intraday PnL, broker sync, optimizer recommendation, or rebalance action exists.
- Durable snapshot persistence belongs to Phase 5L.

