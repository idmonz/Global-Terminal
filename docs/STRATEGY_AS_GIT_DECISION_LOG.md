# Strategy-as-Git Decision Log

## Purpose

Strategy-as-Git stores strategy candidates as research commits. Commits record why a candidate was considered, what data/provider state existed, what guard checks said, and how subsequent tracking payloads can be compared.

## V2 improvements

- Commit diff across config, factors, backtest, OOS, regime, guards, data quality, provider state, linked watchlist, and linked reports.
- Parent-child commit graph payload.
- Review queue states: draft, reviewed, tracked, archived, requires_review.
- Forward tracking snapshot payload.
- Real guard rules that return passed, warning, failed, or skipped_no_data.

## Main functions

- `compare_strategy_commits()`
- `build_strategy_commit_graph_payload()`
- `build_strategy_review_queue_payload()`
- `run_research_guard_pipeline()`
- `build_forward_tracking_snapshot()`

## Tests

Covered by `tests/test_goal11b_strategy_commit_diff_and_guards.py`.


## Research-only policy

This system is for monitoring, inspection, documentation, and research workflow only. It does not perform broker execution, order routing, automatic rebalancing, or trade approval. External widgets are visual supplements only and are never used for calculations, reports, tests, backtests, provider health, or source-freshness scoring.

## Source and caveat policy

Every workflow must label source status, freshness, confidence, and gaps where available. Missing context remains `unavailable`, `missing`, `proxy`, `estimated`, `historical-only`, or `missing-key`; Goal 11B does not fill gaps with random values.

## Goal 11C Productization Update

Goal 11C adds product-quality Research OS UX: shared visual payloads, source freshness chips, command palette state, watchlist action cards/detail/event grid, report reader/review workflow, strategy review queue/artifact timeline, Intel Feed/Live Alerts/View Presets/Layer Panel, Research Tool Center, deeper tests, and release hygiene docs. External projects were inspected as conceptual references only; no external source code was copied or vendored.
