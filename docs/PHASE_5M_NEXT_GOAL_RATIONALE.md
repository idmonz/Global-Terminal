# Phase 5M Next Goal Rationale

Updated: 2026-06-22

## Decision

The next single vertical slice is Phase 5N Source-Backed Symbol Intelligence Depth.

## Why

Phase 5M makes symbol workstations broadly reachable, but most workstations still contain one price chart, static taxonomy, and unavailable exact-symbol news/fundamentals. This is now the largest gap against TradingView chart depth, OpenBB source-aware analysis, Bloomberg-like multi-panel research, and the user's original Streamlit intelligence tabs.

## Required Outcome

Deepen the same canonical workstation with:

- candlestick/line and volume views;
- bounded SMA/EMA, RSI, MACD, volatility, and comparison overlays;
- source-backed equity/ETF financial availability and exact-symbol news;
- source-backed crypto funding, basis, and open-interest context where public endpoints succeed;
- configurable but URL-safe panel state;
- explicit unavailable/provider/error states without inference or advice.

## Why Not Commercial Platform Yet

Hosted auth, billing, multi-user persistence, background delivery, and broker integration would commercialize an analysis surface that is still too shallow. User-facing intelligence depth should reach strong internal-beta quality first.

## Prompting Basis

The next prompt follows current Codex guidance: one focused outcome, authoritative file context, repository-scoped skills, measurable acceptance criteria, reproducible tests, and visual verification. Reusable workflow instructions remain in `.agents/skills`; the execution prompt contains only phase-specific scope and evidence.
