# Phase 5N Release Report

Updated: 2026-06-22

## Planned Final Archive

`dist/global_market_terminal_20260622T094500Z.zip`

The deterministic final release gate was run after all Phase 5N reports and the Phase 5O prompt were present.

- selected files before manifest: 1,400;
- actual ZIP entries: 1,401;
- manifest expected/actual entries: 1,401 / 1,401;
- required Phase 5N/web/backend/skills files missing: 0;
- forbidden external/private/generated/database entries: 0.

## Required Inclusions

- root/repository agent harness and `.agents/skills`;
- Streamlit lab, reusable `lib`, backend API, Next.js source, deterministic fixtures;
- Phase 5N runtime, UI, tests, reports, visual harness, roadmap, scorecard, and next prompt.

## Required Exclusions

- `.env` and secrets;
- `external (2)` and all external archives;
- data/cache, private databases, uploads, models, checkpoints, logs, and screenshots;
- `node_modules`, `.next`, test caches, and review workspace.

The same counts are recorded by `docs/RELEASE_PACKAGE_REPORT.md` and the embedded `release_manifest.json`.
