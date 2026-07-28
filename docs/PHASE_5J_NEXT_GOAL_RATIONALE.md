# Phase 5J Next Goal Rationale

Updated: 2026-06-21

## Decision

The next single vertical slice is Phase 5K: Portfolio And Risk Workstation.

## Why This Slice

The web now supports four complete research journeys: symbol intelligence, global event intelligence, market discovery, and options analysis. The largest remaining Streamlit-to-web gap is portfolio research. `pages/5_Portfolio.py` and `pages/16_Portfolio_Quant_Lab.py` contain holdings, performance, optimization, factors, attribution, correlation, stress, backtest, and report concepts, while the commercial web has no coherent holdings-to-risk workflow.

Portfolio also connects the completed slices: selected market-map symbols become holdings candidates, symbol/options analytics provide instrument context, and geopolitical scenarios can become portfolio stress evidence. This creates more daily B2C value than adding another isolated dashboard.

## Intended Journey

`Portfolio import/manual holdings -> valuation and performance -> allocation/correlation -> factors/attribution -> stress/scenarios -> source-bound report snapshot`

## Guardrail

Phase 5K remains research-only. It must not connect brokerage accounts, place orders, recommend rebalancing, prescribe position sizes, or provide personalized investment instructions. User holdings are private local data, excluded from fixtures and releases. If market history is missing, risk metrics remain unavailable rather than zero-filled.
