# Goal 9 Pre-Flight Report

Generated: 2026-06-11

## Baseline Tests

- `python scripts/run_smoke_tests.py`: passed.
- `python -m pytest -q`: passed, 166 tests.
- `python -m pytest tests/test_release_archive_hygiene.py -q`: passed.

## Canonical Guard Status

Initial guard check found facade/export gaps for canonical Goal 9 names that already existed in sibling modules:

- `lib.openbb_bridge.build_openbb_capability_catalog`
- `lib.portfolio_quant_lab.default_portfolio_rows`
- `lib.portfolio_quant_lab.run_buy_and_hold_backtest`
- `lib.portfolio_quant_lab.run_rebalanced_backtest`
- `lib.portfolio_quant_lab.build_strategy_registry`
- `lib.portfolio_quant_lab.generate_alpha_combinations`
- `lib.war_room.build_global_event_map`
- `lib.war_room.compute_country_instability_score`
- `lib.war_room.compute_signal_convergence`

These were restored as thin compatibility wrappers to the existing implementation modules. The follow-up canonical check passed with `canonical_missing=none`.

## Static Universe Counts

- `static/index_constituents/sp500.csv`: 60 rows, minimum 60.
- `static/index_constituents/nasdaq100.csv`: 30 rows, minimum 30.
- `static/index_constituents/korea_watchlist.csv`: 24 rows, minimum 24.

## OpenBB Optional Boundary Status

- `requirements.txt` remains the base dependency file.
- `requirements-openbb.txt` remains optional.
- Existing OpenBB imports are lazy/safe through `lib.openbb_bridge`.
- Base smoke and pytest runs completed without requiring OpenBB installation.

## Release Hygiene Status

- `.gitignore` exists and excludes `.env`, virtual environments, generated caches, `data/cache/`, `data/private/`, `external/`, recovery folders, logs, bytecode, and Streamlit secrets.
- Existing release archive hygiene test passed.
- No release package build was required at pre-flight; final Goal 9 release validation will rebuild and inspect the package.

## Blockers

No active blockers remain after compatibility-wrapper restoration. Note: this working directory is not currently a Git repository, so git status/history checks are unavailable in this workspace.
