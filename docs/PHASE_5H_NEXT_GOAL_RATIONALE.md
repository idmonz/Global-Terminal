# Phase 5H Next Goal Rationale

Updated: 2026-06-20

## Decision

The next single vertical slice is Phase 5I: Provider-Backed Screener And Market Map.

## Why This Slice

The product now has two coherent journeys: Market Home to symbol intelligence, and Market Home to global event intelligence. The highest daily-use gap is discovery: the current heatmap/screener is shallow and fixture-heavy, so users cannot filter a broad universe, rank candidates, compare factors, and open the chosen symbol without leaving the workflow.

This slice directly addresses the user's concern that the web product still lacks much of the Streamlit intelligence surface and TradingView/Finviz/OpenBB-style market breadth.

## Intended Journey

`Market Home -> Market Map/Screener -> filter/rank -> compare -> AAPL or supported symbol workstation -> back with state`

## Why Not Options Or Portfolio First

Options needs a verified chain provider and stricter quality gates. Portfolio needs persistence, privacy, import, and account-bound state. A provider-backed screener can deliver broader daily B2C value now using existing free-first market, FinanceDatabase taxonomy, heatmap, and symbol-route foundations without pretending to have brokerage or personalized advice capabilities.

