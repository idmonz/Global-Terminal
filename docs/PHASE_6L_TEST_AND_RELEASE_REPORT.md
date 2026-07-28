# Phase 6L Test And Release Report

Updated: 2026-07-10

## Test Gates

- Phase 6J/6K/6L/API/migration focused suite: 55 passed.
- Phase 6K/6L focused regression after repository extraction: 20 passed.
- Full Python suite: 985 collected, 985 passed.
- Expected warnings only: FastAPI TestClient deprecation and two existing
  cointegration collinearity warnings.
- `python -m compileall -q app.py backend lib scripts pages`: passed.
- `python scripts/run_smoke_tests.py`: passed, including identity,
  tenant-research repository, persistence, and sync modules.
- `python scripts/export_api_fixtures.py`: passed, 32 fixtures exported.
- `python scripts/validate_agent_harness.py`: passed, one active plan and six
  repository skills.

## Web And Browser Gates

- `npm --prefix apps/web test`: passed.
- `npm --prefix apps/web run lint`: passed.
- `npm --prefix apps/web run build`: passed with Next.js 16.2.9.
- `npm --prefix apps/web audit --audit-level=high`: 0 vulnerabilities.
- `npm --prefix apps/web run visual:phase6l`: passed after final rerun.
- Phase 6L performance harness: passed all budgets.

## Release Gates

Final archive pattern: `dist/global_market_terminal_<UTC timestamp>.zip`.

- files packaged: 1,678 plus manifest;
- ZIP entries: 1,679;
- configured values checked: 15;
- exact-value hits: 0;
- forbidden entries: 0;
- `.env`, private/QA databases, external archives, `review_workspace`, and
  screenshot evidence are excluded;
- `.env.example`, Phase 6L source/tests/docs, web product, and optional API are
  included.

## Verdict

The Phase 6L local-conformance branch satisfies its exit gate. Hosted proof does
not: Supabase was absent and remains explicitly unavailable. The durable
benchmark goal remains active and Phase 6M is the sole active plan.
