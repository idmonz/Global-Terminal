# Codex Goal 10B To Goal 12E Review Plan

Review date: 2026-06-15

Scope: review gate only. Goal 13A implementation was not started.

## Inputs

- Older baseline ZIP: `../Global Macro + Equity + Crypto + Commodity + Geopolitical Risk Terminal_goal10b.zip`
- Current updated ZIP: `~/Downloads/global_market_terminal_goal12e_inspected_hotfix.zip`
- Markdown report: `C:/Users/chansoo/.codex/attachments/9b18bdc1-b52f-44c9-adf8-9801310ac8b6/pasted-text.txt`

## Extraction Paths

- Old baseline extracted to: `review_workspace/old_goal10b/Global Macro + Equity + Crypto + Commodity + Geopolitical Risk Terminal/`
- Current hotfix extracted to: `review_workspace/current_goal12e_hotfix/`

The extracted source trees were not edited during the initial inspection phase.

## File Counts

- Old baseline initial recursive file count: 4151
- Current hotfix initial recursive file count: 1113
- Current hotfix release manifest selected file count: 1112
- Current hotfix release manifest expected ZIP entry count: 1113
- Current hotfix Python files detected after extraction: 808
- Current hotfix test files detected: 381
- Current hotfix docs files detected: 295

The old baseline count is much larger because it contains external/source-reference and generated material. The current package is intentionally leaner.

## Top-Level Directory Comparison

Old baseline top-level entries:

- `.env`
- `.env.example`
- `.gitignore`
- `app.py`
- `data/`
- `dist/`
- `docs/`
- `external/`
- `lib/`
- `pages/`
- `pytest.ini`
- `README.md`
- `requirements.txt`
- `requirements-openbb.txt`
- `scripts/`
- `static/`
- `tests/`

Current hotfix initial top-level entries:

- `.env.example`
- `.gitignore`
- `app.py`
- `docs/`
- `lib/`
- `pages/`
- `pytest.ini`
- `README.md`
- `release_manifest.json`
- `requirements.txt`
- `requirements-openbb.txt`
- `scripts/`
- `static/`
- `tests/`

Expected package-hygiene improvements are present: the current release no longer ships `.env` or `external/`.

## Detected App Structure

- Main app entry: `app.py`
- Streamlit pages: `pages/`
- Core business/research logic: `lib/`
- Static universe files: `static/index_constituents/`
- CLI/release/probe scripts: `scripts/`

Goal 10B-era terminal/data/provider modules remain present. After excluding private/generated/vendor/release-only folders and `.env`, no old Goal 10B relative source/test/doc paths were missing from the current hotfix package.

## Detected Test Structure

The current test tree contains:

- Goal 10/10B preservation and safety tests.
- Goal 11 through Goal 11F Research OS, command safety, watchlist, alert, report, strategy, and release-hygiene tests.
- Goal 12A through Goal 12E options, quant diagnostics, case index, surface QA, surface review queue, and release-hygiene tests.
- Dedicated hotfix coverage: `tests/test_goal12e_private_path_redaction_hotfix.py`.

Collection result in this environment:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --collect-only` collected 599 tests.

The markdown report's 597-test claim appears to describe the original Goal 12E release before the two hotfix tests, not the inspected hotfix ZIP.

## Detected Docs Structure

The current docs tree includes:

- Architecture, compliance, data-source, and release-hygiene documents.
- Goal reports from Goal 6 through Goal 12E.
- Research OS, options, quant, case-store, surface-QA, and review-queue docs.
- Goal 13 prep doc: `docs/GOAL_13_ACTIONLESS_SIMULATION_ARCHITECTURE_PREP.md`.

## Detected Release Scripts

- `scripts/build_release_zip.py`
- `scripts/safe_cleanup_generated_artifacts.py`
- `scripts/run_smoke_tests.py`
- Provider probe scripts under `scripts/probe_*.py`

## Detected Private, External, And Cache Directories

Old baseline:

- `.env` exists in package.
- `external/` exists in package.
- `data/cache/` exists in package.
- `lib/__pycache__/` exists in package.
- `dist/` exists in package.

Current hotfix initial package:

- `.env` absent.
- `external/` absent.
- `data/cache/` absent.
- `data/private/` absent.
- `__pycache__` absent before verification commands.
- `dist/` absent before verification commands.

Verification commands later generated `data/private/`, `dist/`, and cache/pycache artifacts inside the extracted review copy. Cleanup removed pycache/cache artifacts, and the generated `dist/` was retained as review evidence.

## Commands Run

- `python -m compileall -q app.py lib pages scripts tests`: PASS
- `python scripts/run_smoke_tests.py`: PASS
- Focused Goal 12D/12E pytest set: PASS, 26 tests
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --collect-only`: PASS, 599 tests collected
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`: FAIL on default Windows locale
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONUTF8=1 python -m pytest -q`: PASS
- `python scripts/safe_cleanup_generated_artifacts.py --dry-run`: PASS
- `python scripts/safe_cleanup_generated_artifacts.py --execute`: PASS
- `python scripts/build_release_zip.py`: PASS mechanically, 1113 ZIP entries

## Initial Risk Hypotheses And Findings

1. Core Goal 10B regression risk: low.
   The old relative source/test/doc surface is preserved after excluding expected private/generated/vendor/release-only paths. Smoke and focused tests passed.

2. Goal 11 to Goal 12E feature integration risk: low to moderate.
   Expected Research OS, Options Lab, Surface QA, Case Index, Review Queue, and Goal 13 prep modules/tests/docs are present. Focused Goal 12D/12E tests passed.

3. Hidden execution or unsafe trading-language risk: low based on static scan.
   Static searches found safety filters, command boundaries, and research-only language. No obvious subprocess/shell/eval/live-broker execution pathway was found in app/lib/pages/scripts.

4. Fake data or demo-mode risk: low based on scan.
   Demo/sample paths are explicitly labeled and guarded. The Options Lab demo mode is opt-in.

5. External source copying risk: low for the current hotfix ZIP.
   The current package does not ship `external/`, and external-reference docs describe concept-only use.

6. Private path leakage risk: high.
   `release_manifest.json` in the inspected hotfix ZIP contains absolute build paths such as `/mnt/data/goal12e_inspect`. A local release build also packages absolute user-machine paths in `release_manifest.json`. Some historical docs also retain `/mnt/data/...` paths. This contradicts the private-path hygiene claim.

7. Test reproducibility risk on Windows/Korean locale: high.
   The documented full pytest command fails in this environment because `tests/test_goal11b_no_regression_goal10b.py` calls `Path.read_text()` without `encoding="utf-8"` on `static/index_constituents/korea_watchlist.csv`. The suite passes with `PYTHONUTF8=1`, but the report's command does not reproduce as written.

## Gate Decision

Decision: HOLD for Goal 13A.

The current Goal 12E inspected hotfix is functionally close and preserves the project direction, but it is not clean enough for the Goal 13A gate as-is. Before Goal 13A starts, fix and re-release Goal 12E with:

- No absolute local/build paths in packaged `release_manifest.json`.
- Historical docs scrubbed or explicitly excluded if they contain local build paths.
- Full pytest passing on Windows without requiring undocumented `PYTHONUTF8=1`, or the release gate command/documentation updated consistently.
- Collection count/report wording reconciled for the inspected hotfix ZIP.
