# Phase 5K External Evidence Ledger

Updated: 2026-06-21

No external source, CSS, visual asset, dataset, model weight, screenshot, or brand asset is copied into Phase 5K.

| Project/path | License stance | Semantic review | Behavior adopted | Rejected |
|---|---|---|---|---|
| `OpenAlice-master/ui/src/pages/PortfolioPage.tsx` and `PortfolioSidebar.tsx` | AGPL-3.0, behavior-only | Aggregate overview, per-account context, refresh state, equity curve, dense positions table, empty/error states | Product-first overview, compact state, dense holdings and useful empty/failure behavior | Source, account/broker wiring, styles, components, PnL logic |
| `OpenBB-develop/.../correlation_matrix.py` | AGPL-3.0, behavior-only | Lower-triangle matrix, labels, hover values, diverging scale | Compact readable correlation matrix and explicit matrix semantics | Source, Plotly implementation, styles |
| `quant-traderr-lab-main/RMT_Correlation_Filter/RMT_Pipeline.py` | MIT path reviewed | Eigenvalue summary and Marchenko-Pastur concept | Existing first-party RMT caveat may be shown as diagnostics only | No code copied; no synthetic matrix or 3D neon renderer; no denoised covariance claim |
| `tensortrade-master/tensortrade/oms/wallets/portfolio.py` | Apache-2.0, architecture concepts only | Base-currency valuation and performance state separation | Explicit base currency and portfolio snapshot semantics | Wallet, exchange, order-listener, locked-balance, execution architecture |
| `QuantDinger-main/backend_api_python/app/routes/portfolio.py` | Exact archive license reviewed; behavior-only for this phase | Position validation, grouped valuation, parallel/rate-limited symbol price retrieval, empty summaries | Strict holding validation, symbol-only provider calls, coverage-aware totals | CRUD database code, zero-price fallback, shorts, broker/account data, SQL, alerts |
| `QuantDinger-main/.../portfolio_monitor.py` | Same archive boundary | Scheduled AI monitoring and notifications | None | AI transmission of holdings, scheduled monitoring, alerts, notifications |
| Bloomberg/Koyfin/TradingView public product behavior | proprietary, behavior-only | Dense KPI hierarchy, performance/drawdown context, compact tabs | Information hierarchy and keyboard-readable compact workstation | Branding, assets, screenshots, CSS, proprietary data and recommendation behavior |

## First-Party Acceptance Criteria

- Independent Python and TypeScript implementation.
- Source labels and coverage remain visible without dominating the first viewport.
- Missing data is not represented as zero.
- Demo holdings are fictional and clearly labeled.
- Local-private quantities and costs cannot enter URLs, fixtures, screenshots, logs, external AI, or release ZIPs.
- No trade, rebalance, monitor, alert, or recommendation action is added.

