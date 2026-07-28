# Phase 5I Next Goal Rationale

Updated: 2026-06-20

## Decision

The next single vertical slice is Phase 5J: Options And Quant Workstation.

## Why This Slice

Phase 5I closes the first useful daily discovery loop: a user can inspect a broad-enough 60-equity map, filter and rank it, compare candidates, and open the one verified equity workstation. The user's strongest remaining functional complaint is now options and serious quantitative analysis. Existing Streamlit and `lib/` engines contain options-flow, Greeks, scenario, and factor concepts, but the commercial web product still has no trustworthy chain-driven options workflow.

Options is also the next place where honesty matters most. A polished IV or GEX chart built from missing or stale chain data would be actively misleading. Phase 5J should therefore begin with provider and field-quality proof, then expose calculations only when quote timestamps, expiries, strikes, bid/ask, open interest, and contract multipliers satisfy explicit gates.

## Intended Journey

`Market Home or Symbol Workstation -> Options Quant -> expiry/strike selection -> chain quality -> Greeks/IV surface -> scenario research -> evidence export`

## Why Not Portfolio Or Research Memory First

Portfolio work needs account-scoped persistence, imports, privacy boundaries, and more complete symbol coverage. Research memory is valuable but would mainly preserve today's still-incomplete analysis. A verified options and quant workstation directly restores a major Streamlit capability, expands the daily analytical surface, and creates evidence that later portfolio stress and report memory can reuse.

## Guardrail

No order entry, broker connection, personalized trade recommendation, autonomous action, or buy/sell language belongs in Phase 5J. If no free provider can produce a legally usable and technically adequate live chain, the product must show an explicit limited/unavailable state and ship a deterministic research fixture rather than imply live analytics.
