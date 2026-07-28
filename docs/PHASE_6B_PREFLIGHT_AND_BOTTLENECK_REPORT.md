# Phase 6B Preflight And Bottleneck Report

Updated: 2026-07-01

## Objective

Expand the materialized Market Map beyond 137 rows, materially improve reviewed
classification coverage, and add observable scheduled refresh/history without
moving provider work back into the web request path.

## Toolchain And Configuration

- Python 3.14.5;
- yfinance 0.2.66;
- Node 24.16.0;
- npm 11.13.0;
- FastAPI `127.0.0.1:8004`;
- production Next.js `127.0.0.1:3045`;
- `SEC_USER_AGENT`, `ALPHAVANTAGE_API_KEY`, `FINNHUB_API_KEY`, and
  `GEMINI_API_KEY`: present by key-presence check only.

No credential value was read or printed.

## Baseline Gates

- full Python suite: 866 passed with the existing cointegration and TestClient
  warnings;
- web fixture/runtime test: passed;
- ESLint: passed;
- Next.js production build: passed;
- npm audit: zero vulnerabilities;
- source release: 1,521 entries;
- Phase 6A browser baseline: online API reachable, 137 tiles, visible stale
  last-known-good snapshot, no page overflow or browser errors.

## External Audit

The deterministic audit was rerun under
`review_workspace/external2_analysis/phase6b`:

- 28 archives;
- 51,305 archive entries;
- 38,623 indexed non-vendored text/code files;
- 8,742,912 indexed lines;
- 556 vendored text files and 38 oversized files explicitly skipped;
- zero archive hash changes from Phase 6A;
- 18 direct-use, 6 behavior-only, 3 needs-review, 1 blocked.

Mechanical indexing is not individual semantic human review.

## Runtime Baseline

- materialized rows: 137;
- taxonomy coverage: 60;
- unclassified: 77;
- response: 746,879 bytes;
- warm stored-read curl p50: 49.17 ms;
- warm stored-read curl p95: 78.11 ms;
- read status during preflight: stale, with last-known-good retained.

## Breadth Probe

yfinance's public screener accepts `offset`. Three bounded pages at offsets 0,
250, and 500 returned:

- 250 rows per page;
- zero overlap;
- 750 combined unique symbols;
- provider-reported candidate total: 7,671 at the tested filter.

The provider rows do not include sector/industry fields. Separate batched sector
queries work for the reviewed Yahoo sector vocabulary. Industry-wide discovery
would require roughly 145 provider queries and is rejected as an excessive
background-call design.

## Phase 6B Budgets

- target at least 300 official-listing-matched observations;
- target at least 250 rows with explicit source-aware sector classification;
- preserve local reviewed industry labels where available and keep others
  `Unclassified`;
- broad observation calls at most 3 pages;
- sector classification calls at most 11;
- no provider calls on stored reads;
- compact response below 900 KB;
- stored read p50 below 500 ms and p95 below 900 ms;
- scheduler overlap prevention and bounded refresh history;
- no secrets, private paths, holdings, notes, or user data in snapshots/history;
- no page-level overflow or browser console/page errors.

