# Phase 6H Test And Release Report

Updated: 2026-07-03

## Test Scope

- Full collection: 930 tests.
- Full `python -m pytest -q`: passed.
- Existing warnings only:
  - FastAPI/Starlette TestClient deprecation;
  - two existing cointegration collinearity warnings.
- Phase 6H contract/API/frontend tests cover compact deterministic manifests,
  exact identity, panel provenance, request budgets, change mapping, local
  privacy, ETag/304, unknown 404, fixture boundaries, and saved-primary
  deduplication.
- Phase 6E/6F/6G focused Python regressions: passed.
- Phase 6E, 6F, 6G, and 6H production Chrome harnesses pass.
- Compileall, import smoke, and 32-file fixture export: passed.
- Web fixture/runtime tests, ESLint, and Next.js 16.2.9 production build:
  passed.
- npm high-severity audit: zero vulnerabilities.

## Release Boundary

The final release must include `apps/web`, `backend`, `lib`, `docs`, tests, and
the deterministic public fixtures. It must exclude:

- plaintext `.env` and credential values;
- external archives and extracted references;
- `review_workspace` screenshots/logs;
- `node_modules` and build caches;
- local databases, private notes, and provider response bodies.

Final release:

`dist/global_market_terminal_<UTC timestamp>.zip`

- 1,608 entries including the manifest;
- analyst Python, API, web, tests, fixtures, and Phase 6H documents included;
- plaintext `.env`, external paths, `review_workspace`, `node_modules`,
  databases, and cache paths absent;
- 15 configured environment values checked by exact-byte comparison; zero
  archive entries contained a value;
- `.env.example` remains included as a value-free setup template.

The exact final filename is recorded in `release_manifest.json`.

## Verdict

Phase 6H is complete only as a scoped synchronized-workspace slice. The durable
Web Product Parity Master Goal remains active. Hosted operations, provider SLO
truth, always-on delivery, auth, billing, broader licensed data, and verified
geopolitical layers remain incomplete.
