# Phase 6B Test And Release Report

Updated: 2026-07-01

## Focused Gates

- identity/taxonomy, scheduler/history, snapshot, Phase 5I/5Z compatibility: pass;
- exact detail sidecar and unknown-symbol isolation: pass;
- compact 333-row synthetic payload below 900 KB: pass;
- online/stale/offline browser harness: pass;
- TypeScript/ESLint and production build precursor: pass.

## Measured Runtime Gates

- rows: 333;
- response bytes: 844,358 to 866 KB across the final refreshes;
- stored HTTP p50: 124 ms over 11 samples;
- stored HTTP p95: 248 ms;
- ETag conditional response: 304;
- successful stored read provider calls: zero;
- exact AAPL detail includes CIK and full rank models;
- unknown `ZZZZ`: explicit unknown-symbol, no Apple identity.

## Final Gates

- full Python: 876 passed;
- compileall: passed;
- smoke imports: passed;
- fixture export: 27 validated fixtures;
- web test: passed;
- ESLint: passed;
- Next.js production build: passed;
- npm audit: zero vulnerabilities;
- final online browser rerun: 333 tiles, 1 visible taxonomy conflict, no overflow
  or browser errors.
- release-hygiene regression slice: passed;
- release archive: 1,535 entries including the manifest;
- required Phase 6B runtime, scheduler, visual harness, reports, and Phase 6C
  prompt: present;
- plaintext `.env`, `node_modules`, `.next`, private/cache snapshots,
  `review_workspace`, and external reference archives: absent. The distributable
  placeholder-only `.env.example` is intentionally present.

The release archive is rebuilt and inspected after these documents are included.
