# Phase 5Y Test And Release Report

Updated: 2026-07-01

## Test Results

- focused map/news regression: passed, 27 tests;
- focused URL/map contract regression: passed, 22 tests;
- full Python suite: passed, 100%;
- import smoke: passed;
- Python compileall: passed;
- API fixture export: passed, 27 fixtures;
- web fixture/runtime validation: passed;
- ESLint: passed;
- Next.js production build: passed;
- npm audit at high severity: 0 vulnerabilities;
- online and controlled-offline visual harness: passed;
- core live API smoke: five of five routes returned HTTP 200.

Expected existing warnings:

- Starlette/httpx TestClient deprecation;
- two cointegration collinearity warnings.

## API Smoke

Observed response sizes:

- `/api/runtime-health`: 13,591 bytes;
- `/api/map-news-event-fusion?include_runtime=true`: 631,840 bytes;
- `/api/news?include_runtime=true`: 103,811 bytes;
- `/api/war-room-map-replay`: 212,428 bytes;
- AAPL symbol workstation cache request: 193,793 bytes.

Counts and byte sizes are observational and must not be hard-coded.

## Release Artifact

Artifact:

`dist/global_market_terminal_<UTC timestamp>.zip`

Inspection:

- the final verified build contained 1,498 entries and was approximately 4.19 MB;
- manifest entries: 2;
- forbidden `.env`, `node_modules`, `external (2)`, `review_workspace` and `.git`
  entries: 0;
- `lib/map_news_event_fusion.py`: included;
- `apps/web/src/components/LeafletWarMap.tsx`: included.

## Release Verdict

Phase 5Y passes its scoped release gate. The durable benchmark-parity goal remains
active. This artifact is a local/internal beta package, not a hosted commercial
release with auth, billing, observability or data licensing guarantees.
