# Phase 6A Preflight And Bottleneck Report

Updated: 2026-07-01

## Objective

Move the Market Map request path from synchronous provider composition to an
observable, atomic, materialized snapshot read, then add official SEC company facts
and honest earnings/calendar depth to the AAPL workstation.

## Current Toolchain And Processes

- Python 3.14.5;
- Node 24.16.0;
- npm 11.13.0;
- FastAPI listening on `127.0.0.1:8004`;
- production Next.js listening on `127.0.0.1:3045`;
- local Chrome and Playwright Core available.

Configured key presence was checked without reading or printing values:

- `SEC_USER_AGENT`: present;
- `ALPHAVANTAGE_API_KEY`: present;
- `FINNHUB_API_KEY`: present;
- `GEMINI_API_KEY`: present but not required by this phase.

## Baseline Verification

- the Phase 5Z final full Python regression passed before Phase 6A edits;
- focused market-map, backend, SEC, provider-breadth, and symbol tests: 29 passed;
- existing Starlette/httpx TestClient deprecation remains non-blocking;
- Phase 5Z web test, lint, production build, audit, visual, and release gates pass;
- latest release: 1,508 entries, approximately 4.22 MB, zero forbidden entries.

## External Audit

The required archive audit was rerun:

- 28 archives;
- 51,305 entries;
- 38,623 indexed non-vendored text/code files;
- 8,742,912 indexed lines;
- no archive hash changed from the Phase 5Z audit;
- license classes remain 18 direct-use-allowed, 6 behavior-only, 3 needs-review,
  and 1 blocked.

Artifacts are under `review_workspace/external2_analysis/phase6a/`. This is
mechanical coverage, not a claim of individual human semantic review for every line.

## Runtime Baseline

`GET /api/market-map-screener?include_runtime=true&period=1y`:

- 137 rows;
- 1,868,494 bytes;
- five warm local HTTP observations: 0.544, 0.616, 0.617, 0.639, 0.645 seconds;
- observed warm p50: approximately 0.617 seconds;
- current request still rebuilds the contract even when provider caches are warm.

Final Phase 5Z visual evidence:

- 137 tiles;
- 131 broad official-listed observations;
- 137 official listing identities;
- 60 local taxonomy matches;
- heatmap top 714 px and first tile top 846 px at 1600x1000;
- no horizontal overflow or browser errors.

## AAPL Baseline

Fresh browser verification on the current production build:

- Alpha Vantage and Finnhub breadth panel visible;
- both provider rows cached and source-labeled;
- 12 exact-symbol news rows;
- desktop and 390 px mobile Financials have no horizontal overflow;
- SEC identity lookup exists, but official filing facts are not normalized or shown;
- earnings/calendar is not a first-class contract.

## Primary Bottlenecks

1. The web request path performs broad contract composition instead of reading an
   already materialized observation.
2. The 1.87 MB envelope includes heavy rank/factor detail not required for first
   heatmap paint.
3. No atomic versioned market snapshot, last-known-good fallback, retention, or
   refresh-job health contract exists.
4. No ETag/conditional-read behavior exists for Market Map.
5. SEC integration resolves identity only; facts lack concept/unit/period/form/filed
   provenance.
6. Earnings and calendar rows are absent rather than explicitly ready/unavailable.
7. Refresh operations have no stable structured job event or duration ledger.

## Phase 6A Budgets

- successful materialized read performs zero provider calls;
- warm compact API p50 below 500 ms;
- compact first-paint payload below 900 KB uncompressed;
- atomic last-known-good snapshot survives failed refresh;
- no request-time per-symbol provider fan-out;
- no secret, private path, or private portfolio content in snapshot/log/API data;
- zero browser console/page errors and no page-level overflow.
