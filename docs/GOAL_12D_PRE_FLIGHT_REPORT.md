# GOAL 12D Pre-Flight Report

## Commands run before implementation

- `python -m compileall -q app.py lib pages scripts tests` — passed.
- `python scripts/run_smoke_tests.py` — passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q` — 551 tests passed with 2 warnings.
- `python scripts/build_release_zip.py` — passed; 1047 selected files, 1048 zip entries including manifest.

## Baseline status

Goal 12C was release-hygiene clean with `.env.example` included. Current known gaps were confirmed: top command bar safety inconsistency, IV-based surface QA, option-book 30-day TTE fallback, unknown-model Black-Scholes default, missing options research case store, missing surface QA review queue, and generic external roadmap.

## Scope

Goal 12D implements safety-boundary unification, price-based surface diagnostics, no-fake-TTE option-book stress, unknown-model manual-mode enforcement, private research case store, surface review queue, concrete external roadmap, documentation, tests, cleanup, and release build.
