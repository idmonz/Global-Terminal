# Goal 11F Pre-flight Report

Generated: 2026-06-14T13:56:19.531908+00:00

## Baseline commands run before patching

| Command | Result |
|---|---|
| `python -m compileall -q app.py lib pages scripts tests` | PASS |
| `python scripts/run_smoke_tests.py` | PASS |
| `python -m pytest -q` | PASS |
| `python scripts/build_release_zip.py` | PASS; baseline selected file count was 845 |

## Setup status before hotfix

- Project root `.env.example`: missing in the Goal 11E release baseline.
- Release zip `.env.example`: absent in the Goal 11E release baseline.
- `.env` and `.env.*` secret files: excluded.

## Command safety matrix before hotfix

| Category | Example | Goal 11E status | Goal 11F target |
|---|---|---:|---:|
| Advisory intent | advisory language for a single ticker | under-blocked | blocked boundary card |
| Portfolio advisory intent | portfolio-superlative phrasing | under-blocked | blocked boundary card |
| Guarantee phrasing | guaranteed/risk-free/profit-guarantee language | under-blocked | blocked boundary card |
| Descriptive phrase | hold period / holding return analysis | over-blocked or fragile | allowed |
| Market-structure phrase | exit liquidity / order flow | over-blocked or fragile | allowed |

## Report export status before hotfix

`export_report_html()` sanitized Markdown fallback but could write `html_body_optional` directly.

## Command routing status before hotfix

Some Energy Brief labels were routed through the War Room workflow command.

- Scope: Goal 11F hotfix only; Goal 12 was not implemented.
- Boundary: research-only local workspace, no broker path, no autonomous execution path, no external runtime dependency.
- Verification gates: compileall, smoke tests, full pytest, cleanup dry-run, cleanup execute, and release build.
