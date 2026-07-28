# Goal 12E Repackaged Hotfix Report

Generated: 2026-06-15

## Scope

This is a Goal 12E hotfix and release-gate repackaging only. Goal 13A was not implemented.

## Inputs

- Source ZIP used: `~/Downloads/global_market_terminal_goal12e_inspected_hotfix.zip`
- Active workspace: `release_root`
- Prior review artifact: `docs/CODEX_GOAL10B_TO_GOAL12E_REVIEW_PLAN.md`

## Workspace Update Summary

- Promoted the inspected Goal 12E hotfix source, docs, tests, scripts, static files, and app entrypoint into the active workspace.
- Preserved `.env`.
- Removed the stale Goal 10B-era `external/` source-reference tree after full pytest identified it as a runtime release-gate violation.
- Left local generated/private areas out of the release package through the release manifest filters.

## Fixes Made

- Reworked `scripts/build_release_zip.py` so packaged `release_manifest.json` uses release-safe metadata only:
  - `project_root_label: "release_root"`
  - `zip_name`
  - `zip_path: "dist/<zip-name>"`
- Updated the release builder to write a sanitized workspace `release_manifest.json`.
- Constrained workspace manifest writes to normal `dist/` release builds so temp/test builds cannot clobber the handoff manifest.
- Added release exclusions for local Codex review artifacts, SQLite/database files, model weights/checkpoints, and local/uploaded option-chain filename patterns.
- Updated `scripts/safe_cleanup_generated_artifacts.py` so cleanup logs no longer write absolute project roots.
- Scrubbed historical release docs that contained local build paths.
- Fixed Windows locale reproducibility by adding explicit `encoding="utf-8"` reads for static universe CSV checks.
- Reconciled Goal 12E test-count wording to the current repackaged-hotfix collection count.

## Tests Added Or Updated

- Updated `tests/test_goal11b_no_regression_goal10b.py` for explicit UTF-8 CSV reads.
- Expanded `tests/test_goal12e_release_hygiene.py` to build a release ZIP, open it, and assert that packaged `release_manifest.json` and release docs do not contain private/build path markers.
- Expanded release-hygiene checks for database/model/uploaded option-chain artifact exclusions.

## Validation Results

- `python -m compileall -q app.py lib pages scripts tests`: PASS
- `python scripts/run_smoke_tests.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --collect-only`: PASS, 600 tests collected
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`: PASS, 600 tests
- Focused Goal 12D/12E regression set: PASS, 49 tests
- `python scripts/safe_cleanup_generated_artifacts.py --dry-run`: PASS, 7 generated artifacts detected in the final prebuild cleanup run
- `python scripts/safe_cleanup_generated_artifacts.py --execute`: PASS, 7 generated artifacts removed in the final prebuild cleanup run
- `python scripts/build_release_zip.py`: PASS

## Release Artifact

- Handoff ZIP path: `~/Downloads/global_market_terminal_goal12e_repackaged_hotfix.zip`
- Internal release ZIP path: `dist/<timestamped-release-zip>`
- Release ZIP entry count: 1114

## Release Hygiene Verification

- `.env`: excluded
- `data/private/`: excluded
- `data/cache/`: excluded
- `external/`: absent from workspace and excluded by release builder
- `dist/`: excluded
- `__pycache__/` and `.pytest_cache/`: removed by cleanup and excluded
- SQLite/database files: excluded by suffix
- Uploaded/local option-chain files: excluded by filename-token policy
- Model weights/checkpoints: excluded by suffix and filename-token policy
- Packaged `release_manifest.json`: sanitized path metadata only
- Packaged release docs private path scan: PASS

## Windows Locale Reproducibility

The release gate command `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` now passes on this Windows/Korean-locale environment without requiring `PYTHONUTF8=1`.

## Decision

GO for a later, separate Goal 13A gate. Goal 12E is repackaged with the two release-gate blockers fixed, and Goal 13A remains unimplemented.
