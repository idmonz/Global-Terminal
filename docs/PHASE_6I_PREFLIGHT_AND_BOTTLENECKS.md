# Phase 6I Preflight And Bottlenecks

Updated: 2026-07-04

## Baseline Verdict

PASS. Phase 6H is internally consistent and Phase 6I can proceed as a scoped
operational-trust slice.

- Python 3.14.5, Node 24.16.0, npm 11.13.0.
- Alpha Vantage, Finnhub, Gemini, and OpenSky variables are configured by
  presence-only inspection. No value was printed.
- 28 required external archives are present.
- Compileall and import smoke passed.
- 930 tests were collected and the full fail-fast suite passed.
- Existing warnings are one FastAPI/Starlette TestClient deprecation and two
  cointegration collinearity warnings.
- Fixture export produced 32 files.
- Web fixture/runtime tests, ESLint, Next.js production build, and npm audit
  passed; npm reported zero vulnerabilities.
- Baseline release:
  `dist/global_market_terminal_20260704T040830Z.zip`, 1,608 entries.

The working tree is entirely untracked, so Git diff cannot establish ownership.
Current file contents are the baseline and unrelated files must not be reverted.

## Required Harness

The durable goal, Phase 6I prompt, root and web agent rules, workflow, review
checklist, and all six repository skills were read. The relevant external
agent-skills process references were also inspected: contract-first API design,
browser verification, frontend engineering, incremental delivery,
observability, performance, security, shipping, and TDD.

The in-app Browser was retried after reading its complete setup guidance. No
browser backend was available. The repository production Playwright/Chrome
harness remains the required visual fallback.

## External And Benchmark Gate

The deterministic audit was rerun under
`review_workspace/external2_analysis/phase6i`.

| Disposition | Count |
|---|---:|
| Direct-use-allowed | 18 |
| Behavior-only | 6 |
| Needs exact-path review | 3 |
| Blocked | 1 |

All supplied OpenBB, TradingView, terminal, Finviz, WorldMonitor, newsroom,
War Room, and heatmap images were personally inspected. The relevant Phase 6I
behavior is:

- OpenBB: source, metadata, presentation, and linked parameters belong to one
  panel contract.
- TradingView and the Korean terminal reference: exact symbol/time context and
  dense operational state must remain secondary to useful market evidence.
- WorldMonitor: health is derived from observed seed/refresh cadence and stale
  thresholds, not from the existence of a configuration key.
- BB-Terminal: polling cadence and provider limits must be visible; polling is
  not streaming.
- Finviz and map references remain useful product evidence but are not copied
  into this operations slice.

OpenBB, WorldMonitor, OpenStock, BB-Terminal, and worldview remain
behavior-only for the paths reviewed. No external code, asset, dataset, font,
or trade dress will be copied.

## Current Official Evidence

- Alpha Vantage documents a standard free usage limit of 25 requests per day:
  https://www.alphavantage.co/premium/
- Finnhub documents a free-plan limit of 60 calls per minute and returns HTTP
  429 when limits are exceeded:
  https://api.finnhub.io/pricing
  https://finnhub.io/docs/api/stock-newsroom
- SEC scripted access currently allows at most 10 requests per second and
  requires a declared user agent:
  https://www.sec.gov/about/webmaster-frequently-asked-questions
- yfinance documents research/educational and personal-use constraints for the
  underlying Yahoo data:
  https://ranaroussi.github.io/yfinance/index.html
- OpenBB documents source-aware widgets and linked parameters:
  https://docs.openbb.co/workspace/analysts/widgets/overview
- WCAG 2.2 status messages require programmatically determinable progress and
  result updates without unnecessary focus movement:
  https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html

These are current operational inputs, not a grant of commercial redistribution
rights. Provider terms remain a separate commercial-readiness gate.

## Bottlenecks

1. Exact panels can show yfinance and SEC evidence while Runtime Health reports
   zero providers because panel fetches do not enter the shared `DataResult`
   memory ledger.
2. Retrieval time and market/event observation time are not classified against
   a panel-specific SLO in one contract.
3. Panel refresh buttons call providers independently and do not expose a
   precomputed exact-workspace budget.
4. Last attempt, last successful observation, and same-symbol LKG are held in
   separate modules and are not visible together.
5. There is no exact-symbol refresh job identity, bounded event history,
   overlap state, or next-safe-retry explanation.
6. Existing Watchlist materialization has useful budget/LKG patterns, but it
   is a five-symbol workflow and must not be reused as broad fan-out.
7. The local scheduler exists but is not installed, hosted, or always-on.

## Architecture Decision

- Add a project-native `research_operations.v1` contract.
- Persist only bounded, public operational metadata in the existing
  local-private SQLite boundary.
- Record exact panel observations when a panel endpoint returns, then reconcile
  Runtime Health from those observed records plus the existing in-memory
  ledger.
- Add one per-symbol, idempotent, bounded refresh job. It may refresh only an
  allowlisted exact panel set and must compute the hard ceiling before work.
- Preserve matching panel cache/LKG on failure. Never substitute a different
  symbol.
- Keep the worker process-local and truthfully report that no installed service,
  hosted scheduler, notification delivery, or remote control exists.

## Threat And Abuse Cases

- Reject unknown symbols, unknown panels, path traversal, and unsafe URLs.
- Never accept a user-supplied provider URL or provider call count.
- Never serialize credentials, environment values, provider bodies, private
  notes, database paths, stack traces, or unbounded history.
- Bound panel count, provider calls, event history, job retention, and retry
  cadence.
- Prevent same-symbol overlapping jobs and make equal requests idempotent.
- Do not retry automatically after rate limiting or provider failure.
- Do not claim broker execution, alert delivery, autonomous AI, hosted
  persistence, or always-on operation.

## Phase 6I Exit Gate

One exact workspace must visibly and contractually prove panel SLOs, observed
provider health, planned/actual call budget, queued/running/terminal job states,
last attempt versus last success, same-symbol LKG, and next safe retry. Desktop,
390px mobile, offline, stale, rate-limited, overlap, recovery, invalid-input,
and Phase 6H state-preservation gates must pass.

