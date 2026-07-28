# Phase 5O Product And Factor Contract

Updated: 2026-06-22

## User Journey

`Market Home -> Market Discovery -> combine filters -> inspect rank contributions -> save local screen -> open symbol workstation -> return to the same public screen state`

## Public State

Only bounded identifiers may enter the URL:

- universe;
- sector set;
- market-cap, return, volatility, RSI, trend, valuation, and data-quality buckets;
- rank model;
- display mode;
- selected and comparison symbols;
- runtime mode.

Saved-screen names, notes, database identifiers, private symbols, local paths, account data, and secret values never enter the public URL.

## Batch Data

- Market observations: one yfinance multi-symbol history request for the bounded universe.
- Financial snapshot: one yfinance Yahoo screener request, intersected with the bounded registry.
- Static taxonomy and approximate market-cap fallback remain separately labeled `static/proxy`.
- No per-symbol financial or news calls are allowed in the discovery request.

## Factors

Each factor publishes formula, direction, minimum inputs, null policy, provider, market-as-of, retrieval time, caveat, and data gap.

- one-day and one-month return;
- 20-day realized volatility;
- drawdown from running high;
- RSI(14);
- price versus SMA(20);
- market capitalization;
- trailing/forward P/E and price-to-book availability;
- EPS availability/positivity;
- source/data completeness.

Missing factors remain null. Rows are excluded from a selected model when required factors are missing.

## Rank Models

- `balanced`: momentum, inverse volatility, drawdown resilience, trend, valuation, and completeness.
- `momentum`: one-month return, one-day return, trend, RSI position, and volume state.
- `risk_adjusted`: one-month return, inverse volatility, and drawdown resilience.
- `quality`: earnings/valuation availability, positive EPS, market-cap stability proxy, and completeness.

Every model has a version, formula, required factors, score, row eligibility, exclusion reasons, and named contributions. Contributions reconcile to the displayed score within 0.02 points.

The `quality` model is a public-data financial-coverage proxy, not a claim about intrinsic company quality.

## Visual Contract

The first desktop viewport shows:

- universe, provider, market-as-of, retrieval state, and result count;
- compact composable filters;
- rank and display controls;
- a nonblank heatmap/table/scatter/factor surface;
- selected-row rank contribution and source detail;
- compact saved-screen controls.

At 390px, filters collapse into stable groups, the analytical surface keeps a useful minimum width, and tables scroll rather than crush columns.

## Safety

Ranks and filters are descriptive research tools. They do not predict returns, recommend securities, size positions, approve trades, or execute orders.
