# Phase 6I Implementation Report

Updated: 2026-07-04

## Outcome

Phase 6I turns the Phase 6H analyst workspace into an operationally observable
research surface. One exact symbol can now expose provider observations,
separate retrieval and market/event clocks, panel SLOs, a precomputed refresh
budget, bounded queue state, LKG retention, and next-safe-retry truth.

The durable Web Product Parity Master Goal remains active.

## Product Changes

- `research_operations.v1` is implemented in
  `lib/research_operations.py`.
- SQLite schema v9 adds bounded refresh jobs and panel observations.
- Exact refresh is limited to an allowlisted symbol/panel request and eight
  logical provider operations.
- Same-symbol active work is idempotent or rejected as overlap.
- Terminal states distinguish completed, partial, rate-limited, failed, and
  cancelled work.
- A provider failure with usable cached/stale rows is partial, never completed.
- Last attempt and last successful job remain separate.
- Configured provider credentials are not counted as contacted or successful.
- Runtime health now merges bounded panel observations with existing provider
  health evidence.

## API And Web

Added:

- `GET /api/analyst-workspace/{symbol}/operations`
- `POST /api/analyst-workspace/{symbol}/refresh`
- `GET /api/research-operations/jobs/{job_id}`

The Next.js same-origin proxy allows only the exact operations paths and a
bounded JSON POST. The analyst workspace now has:

- observed/configured-only provider counts;
- queue and progress state;
- actual/planned call budget;
- last success and next safe retry;
- one exact-workspace refresh action;
- provider/status/SLO evidence per visible panel;
- polite accessible status announcements.

Panel refresh buttons use the same queue and cannot bypass budget truth.

## Performance Correction

The first benchmark found cached chart-core p95 at 542.83 ms. Repeated cache
hits were redundantly writing identical panel observations. A five-second,
64-entry exact-panel response cache now absorbs short duplicate reads, and
only newly composed delivery is observed. Refresh submission invalidates the
same-symbol response cache.

Final cached chart-core p95 is 22.90 ms with zero provider calls.

## Live Evidence

The final AAPL operations read reported:

- 7 observed providers and 5 configured-only providers in the inspected web
  session;
- an eight-call hard ceiling;
- 6 actual calls, 2 cache hits, 2 stale hits, and 2 failed calls;
- terminal status `partial`;
- retained LKG and an explicit provider-recovery window;
- a prior completed job retained separately as last success.

AAPL displayed 308.63 USD and 62 yfinance OHLCV rows. An independent market
lookup returned the same 308.63 USD value. The US holiday/session boundary is
shown as stale cache rather than live.

## Clean-Room And Provider Policy

The external audit covered all 28 required archives. External code and supplied
screenshots were used as behavior/design evidence only under the existing
license matrix. No AGPL, NASA, unclear-license source, dataset, font, image, or
trade dress was copied.

Official constraints informed the budget:

- Alpha Vantage free standard usage: 25 requests/day;
- Finnhub free usage: 60 calls/minute and personal-use terms;
- SEC fair access: no more than 10 requests/second.

## Remaining Truth

- The worker is process-local, not installed or hosted.
- There is no automatic retry loop, external notification delivery, remote
  control, broker action, auth, billing, or tenant isolation.
- Alpha Vantage and Finnhub free terms are not sufficient evidence for a
  commercial B2C data license.
- Market-session-aware SLO policy should replace the current static targets in
  a later phase.

Outputs are research information only, not financial advice or execution.
