# Phase 6N Test And Release Report

Updated: 2026-07-14

## Python Gates

- focused Phase 6N/6M implementation and visual-harness regression slice:
  26 passed;
- full `python -m pytest -q`: 1,038 collected, all passed after the hosted
  migration/conformance-harness addendum;
- warnings: one existing Starlette/httpx deprecation and two existing
  cointegration collinearity warnings;
- `python -m compileall -q app.py lib pages scripts tests backend`: pass;
- deterministic fixture export: 33 JSON files generated;
- smoke importer and agent-harness validator: pass, six skills, one active
  plan, no missing files or validation errors.

The final external-inventory rerun also exposed and fixed a late-failing path
normalization defect in `scripts/audit_phase5f_external.py`: a relative
`--external-dir` is now resolved before the archive scan and summary path is
written.

## Web And Runtime Gates

- `npm.cmd --prefix apps/web test`: pass; 29 `phase_2b.v1` fixtures plus the
  runtime UI boundary validated;
- `npm.cmd --prefix apps/web run lint`: pass;
- `npm.cmd --prefix apps/web run build`: pass on Next.js 16.2.9;
- `npm.cmd --prefix apps/web audit --audit-level=high`: zero vulnerabilities;
- `npm.cmd --prefix apps/web run test:runtime-api`: pass for runtime API,
  runtime fallback, exact-symbol API/fallback, and Daily Brief API paths;
- the approved-machine visual handoff reused or started FastAPI/Next, while
  the capture itself made zero market-provider requests.

## Performance And Provider Gates

The final 100-sample Phase 6N benchmark passes:

- 25-symbol-equivalent planning p95: 0.884ms against 50ms;
- five-symbol atomic persist/diff p95: 19.014ms against 75ms;
- Attention compose p95: 0.401ms against 75ms;
- Attention filter/rank p95: 0.030ms against 50ms;
- run summary: 3,528 bytes against 35,000 bytes;
- provider calls during Attention triage: 0.

Controlled source-backed, same-day replay, cache-only, offline partial/LKG,
and zero-triage-call evidence remain green. These local timings do not claim
hosted Supabase or upstream-provider latency.

## Visual Gate

The user-run approved handoff and independent verifier both pass:

- evidence contract: `phase6n.visual.v1`;
- screenshots: 23 total, 13 mandatory;
- corrected 390px first material row: y=720;
- desktop ProductNav width: 168px;
- keyboard focus: visible 2px solid outline;
- live regions: 1;
- horizontal overflow, duplicate IDs, unlabeled controls, unexpected browser
  errors, and provider requests: 0;
- progress/completed, six recovery states, runtime offline, News/Brief/Map/
  Analyst drilldown-return, Account A/B isolation, optimistic conflict, local
  retention, and Phase 6H-6M regression surfaces are all captured.

Every image was personally inspected. A local pixel scan confirmed that the
intermittent black region shown by the image viewer was a viewer artifact, not
PNG corruption.

## External Audit

All 28 requested archives were mechanically re-audited with zero read errors.
The two intentionally different coverage metrics are:

- full archive inventory: 51,305 entries, 39,622 text candidates,
  10,596,233 lines, and 249,590 indexed symbols;
- clean-room non-vendored line inventory: 38,623 indexed text/code files and
  8,742,912 lines, with 556 vendored text files excluded.

License classification remains 18 direct-use-allowed, six behavior-only,
three needs-review, and one blocked. Mechanical inventory is not a claim that
every line is semantically approved for reuse.

## Release Gate

Final accepted artifact is the newest timestamped
`dist/global_market_terminal_*.zip` recorded in
`docs/RELEASE_PACKAGE_REPORT.md`.

- 1,748 selected project files plus one embedded manifest;
- 1,749 actual entries, exactly matching the manifest;
- required AGENTS/skills, web, backend, API requirements, docs, tests, scripts,
  static, pages, lib, and Supabase sources are present;
- 24 configured values checked;
- exact-value hits: 0;
- forbidden entries: 0;
- `.env`, external references, private data, databases, logs, `node_modules`,
  `.next`, caches, and generated review evidence are absent.

## Verdict

Phase 6N is complete for its scoped local-first product contract. The
source-backed observation journey, recovery semantics, responsive visual
matrix, tests, benchmark, external audit, and release gate all pass.

This does not claim benchmark parity or hosted commercial readiness. The Phase
6N Supabase migration is now deployed and schema/permission/anonymous-denial
evidence passes. Password-authenticated hosted A/B observation conformance also
passes as of 2026-07-15; recovery evidence remains open. The durable
product-parity goal therefore remains active and advances to Phase 6O.
