# Phase 6E Preflight And Transfer Profile

Updated: 2026-07-03

## Goal And Harness

Phase 6E follows the durable Web Product Parity Master Goal. The product remains
in progress: this phase is a measured delivery and daily-monitoring slice, not a
benchmark-parity completion claim.

The repository `AGENTS.md`, Codex workflow/review checklist, product-parity
harness, clean-room reference process, visual QA gate, release gate, and
next-goal writer were reviewed before implementation. Relevant external
agent-skills were also read in full: API/interface design, browser testing,
incremental implementation, observability, performance, security, shipping,
and test-driven development.

## Environment And Secrets

- Python: `3.14.5`
- Node.js: `24.16.0`
- npm: `11.13.0`
- `.env` presence-only checks: Alpha Vantage, Finnhub, Gemini, and both OpenSky
  OAuth values are present.
- No secret value was printed, copied into a fixture, or written to this report.

## External Reference Audit

The deterministic audit was rerun against all 28 required archives into
`review_workspace/external2_analysis/phase6e`.

- archives: 28
- license disposition: 18 direct-use allowed, 6 behavior-only, 3 needs review,
  1 blocked
- no external source, screenshot asset, dataset row, font, or trade dress is
  copied by this phase

Phase 6E uses benchmark behavior only: summary-first delivery, exact-symbol
panel isolation, shared parameters, advanced list modes, and honest source
status.

## Measured Phase 6D Baseline

Warm local production measurements used AAPL, equity, `1d / 3mo`, cache mode.

| Surface | Bytes | p50 | p95 | Finding |
|---|---:|---:|---:|---|
| direct asset initial HTML/RSC | 1,071,676 | 1,186 ms | 1,404 ms | blocks on all fixtures and eager panels |
| exact summary API | 19,427 | 23.7 ms | 24.2 ms | already within Phase 6E latency target |
| exact chart API | 164,614 | 222 ms | 235 ms | duplicates history, price series, technical series, and analysis charts |

The primary bottleneck is transfer and server serialization, not the compact
summary endpoint. `page.tsx` loads the approximately 20 MB static full
workstation fixture and the complete fixture catalog before rendering an asset
route. The chart delivery repeats the same observations in `history`,
`candles`, `volume`, close/MA series, and technical charts.

## Benchmark Behaviors Reviewed

- TradingView advanced watchlists: Price, Financials, Performance, Risk, and
  Technical modes; sorting and grouping.
- OpenBB Workspace: exact shared parameters, linked widgets, interactive tables,
  and source-aware self-contained panels.
- Next.js App Router: keep the initial Server Component payload small, pass only
  serializable initial data, use client transitions, and lazy-load optional
  client surfaces.

## Phase 6E Implementation Decision

1. Add compact exact-symbol `chart-core` and `technicals` deliveries without
   breaking the existing `chart` contract.
2. Return the asset route before `loadAllFixtures()` and hydrate a progressive
   client workstation from the compact summary.
3. Use a same-origin Next.js runtime proxy backed by a server-only environment
   variable, removing the asset client from stale build-time public API URLs.
4. Add bounded watchlist analysis modes derived from existing materialized
   cache only. Sorting and grouping remain client-side and must not trigger
   provider fan-out.
5. Prove online, offline, unsupported, and unknown-symbol states with payload,
   ETag, performance, desktop, and mobile gates.

## Initial Gate Status

- deterministic external audit: pass
- web fixture/runtime validation: pass
- baseline lint: pass
- baseline full Python suite: pass

Final results and post-change measurements belong in the Phase 6E test,
performance, visual, and release reports.
