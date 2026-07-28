# Phase 5G Release Report

Updated: 2026-06-19

## Required Inclusions

- Root `AGENTS.md`.
- `.agents/skills` six first-party skills and generated metadata.
- Next.js product source and lockfile.
- Optional FastAPI source and API requirements.
- Python engines, pages, tests, fixtures, scripts, and current documentation.

## Required Exclusions

- `.env`, secrets, private data, databases, uploads.
- `external*` archives and external source trees.
- `node_modules`, `.next`, caches, logs, models, checkpoints, and release output directories.

## Status

Selection and built-archive hygiene tests pass.

- ZIP: `dist/global_market_terminal_20260619T151500Z.zip`
- selected files before manifest: 1295
- ZIP entries after manifest: 1296
- external/private/secret/generated trees: excluded

The same counts are reconciled in `docs/RELEASE_PACKAGE_REPORT.md` and `release_manifest.json`.
