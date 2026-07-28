# Goal 11B Release Hygiene Report

Generated: 2026-06-13T13:30:42.912439+00:00

## Rules

Release package must exclude private state, external references, generated artifacts, logs, caches, and secrets.

## Regression test

`tests/test_goal11b_release_hygiene_regression.py` checks `scripts.build_release_zip.iter_release_files()` excludes:

- `external/`
- `data/private/`
- `.db`, `.sqlite`, `.sqlite3`
- `agent-skills-main`

It also verifies `.gitignore` is included.
