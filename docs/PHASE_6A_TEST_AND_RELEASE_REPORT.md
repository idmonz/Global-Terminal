# Phase 6A Test And Release Report

Updated: 2026-07-01

## Gates

- Phase 6A and related focused tests: 27 passed.
- Full Python suite: 866 passed.
- `python -m compileall -q app.py lib pages scripts tests backend`: passed.
- `python scripts/run_smoke_tests.py`: passed.
- `python scripts/export_api_fixtures.py`: 27 fixtures validated/exported.
- `npm --prefix apps/web test`: passed.
- `npm --prefix apps/web run lint`: passed.
- `npm --prefix apps/web run build`: passed.
- `npm --prefix apps/web audit --audit-level=high`: 0 vulnerabilities.
- online/stale/offline Phase 6A browser harness: passed.

Warnings are limited to the existing cointegration collinearity warning and a
Starlette TestClient deprecation warning.

## Security And Privacy

- no API key values were printed or returned;
- snapshots reject secret-like values, private holdings, private notes, and local
  paths;
- unknown-symbol lookup is exact and cannot fall back to AAPL;
- refresh errors are generic and secret-safe;
- SEC user-agent configuration is never exposed.

## Release

- artifact pattern: `dist/global_market_terminal_<UTC timestamp>.zip`;
- inspected build: 4.26 MB and 1,521 entries;
- required Phase 6A runtime, visual harness, reports, and next prompt: present;
- `.env`, `node_modules`, `.next`, private data, materialized cache, and
  `review_workspace`: absent.
