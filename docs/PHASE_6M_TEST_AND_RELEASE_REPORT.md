# Phase 6M Test And Release Report

Updated: 2026-07-13

## Test Gates

- focused Phase 6M contract/API/frontend/performance tests: pass;
- fixture export regression initially exposed a stale expected-file list;
  `attention-desk.json` was added and the regression rerun passed;
- full `python -m pytest -q`: pass, 1007 tests collected;
- warnings: one existing Starlette/httpx deprecation and two existing
  cointegration collinearity warnings;
- `python -m compileall -q app.py lib backend scripts pages`: pass;
- fixture export: 33 files; validators pass;
- agent harness validator: pass with six skills and exactly one active plan.

## Web And Runtime Gates

- `npm --prefix apps/web test`: pass;
- `npm --prefix apps/web run lint`: pass;
- `npm --prefix apps/web run build`: pass on Next.js 16.2.9;
- `npm --prefix apps/web audit --audit-level=high`: 0 vulnerabilities;
- Attention, Watchlist, Analyst, News, Daily Brief, War Map, provider-health,
  runtime-health, and public Attention routes returned HTTP 200;
- browser and performance harnesses pass with zero hidden/provider requests.

## Release Gate

The final source archive contains 1,700 entries including its manifest. Security
inspection checked 18 configured values and found zero exact-value hits and zero
forbidden entries. The archive excludes external references, `.env`, private
databases, visual workspaces, generated framework output, and dependencies.

## Verdict

Phase 6M is complete as a local-first daily Attention journey. Hosted Supabase
and benchmark parity are not complete, and the durable master goal remains
active.
