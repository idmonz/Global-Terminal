# Goal 13A Release Hygiene Report

Generated: 2026-06-15

## Release Boundary

Goal 13A release packaging preserves the Goal 12E sanitized manifest behavior and adds explicit private-root and artifact exclusions for action-less simulation cases.

## Exclusions

- `.env`, `.env.*` except `.env.example`, and `secrets.toml`.
- `data`, `data/cache`, `data/private`, and `data/private/actionless_simulations`.
- `dist`, `.git`, `.pytest_cache`, `__pycache__`, and local recovery/generated artifacts.
- External ZIPs and extracted external reference trees.
- SQLite/database files, logs, local option-chain uploads, provider probe outputs, model weights, checkpoints, and model binary formats.

## Cleanup Results

- `python scripts/cleanup_release_artifacts.py --dry-run`: PASS, 7 generated artifact targets detected.
- `python scripts/cleanup_release_artifacts.py`: PASS, 7 generated artifact targets removed.

## Package Results

- Release ZIP path: `dist/global_market_terminal_20260615T103556Z.zip`
- ZIP entry count: 1140
- Manifest selected file count: 1139
- Manifest project root label: `release_root`
- Manifest zip path: `dist/global_market_terminal_20260615T103556Z.zip`

## Inspection Checklist

- `.env` entries: excluded.
- `data/private` entries: excluded.
- `data/private/actionless_simulations` entries: excluded.
- External ZIP entries: excluded.
- Model weights/checkpoints: excluded.
- Absolute local paths in packaged manifest: not present.
- Goal 13A docs: included.
- Goal 13A tests: included.

## Decision

GO. Final package inspection passed.
