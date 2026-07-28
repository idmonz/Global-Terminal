# Phase 5Z Test And Release Report

Updated: 2026-07-01

## Passed Gates

- focused market-map/screener/symbol suite: 35 passed;
- Phase 5Z plus backend route regression after response optimization: 9 passed;
- full Python regression: passed;
- `python -m compileall -q app.py lib pages scripts tests backend`: passed;
- `python scripts/run_smoke_tests.py`: passed;
- fixture export: 27 JSON-safe fixtures;
- `npm --prefix apps/web test`: passed;
- ESLint: passed;
- Next.js production build: passed;
- npm high-severity audit: 0 vulnerabilities;
- online and controlled-offline Playwright visual suites: passed;
- API smoke: HTTP 200, 137 rows, compact JSON response;
- release ZIP inspection: finalized after documentation update.

Existing non-blocking warnings:

- Starlette/httpx TestClient deprecation;
- two existing cointegration collinearity warnings.

## Security And Privacy

- fixture/API validation found no secret-like values or local private paths;
- `.env` values were not printed or copied;
- release packaging excludes `.env`, caches, databases, external archives,
  screenshots, `review_workspace`, and `node_modules`;
- invalid/unknown symbols cannot inherit AAPL payloads;
- market-map URL state contains public filters and symbols only.

## Release Artifact

The final package contains 1,508 entries including one manifest, is approximately
4.22 MB, and has zero forbidden entries under the release scanner. The exact
timestamped path and selected-file details are recorded by
`scripts/build_release_zip.py` and `docs/RELEASE_PACKAGE_REPORT.md`.

Phase 5Z is a completed scoped slice. The durable master parity goal remains active.
