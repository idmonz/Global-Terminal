# Phase 6D Test And Release Report

Updated: 2026-07-02

## Focused Verification

`tests/test_phase6d_watchlist_desk.py` covers:

- named list CRUD/order/privacy exclusion;
- unknown and asset-class mismatch isolation;
- bounded materialization and overlap protection;
- summary work exclusion for financial/news providers;
- exact panel isolation;
- ETag/private/404 HTTP behavior.

Fixture expectations now include `watchlist-desk.json`. The smoke module list
includes `lib.watchlist_desk`.

## Product Gates

Final results are recorded after the release run:

- focused watchlist/workspace/API tests: pass;
- Python full suite: pass;
- compileall and smoke imports: pass;
- fixture export: 28 files;
- web fixture/runtime test, lint, and production build: pass;
- npm high-severity audit: zero vulnerabilities;
- online/failure/offline Playwright visual gates: pass.

The release remains source-only. Local private databases, `.env`, runtime logs,
review screenshots, caches, and dependency trees are excluded.

