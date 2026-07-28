# Provider / Data Quality Report Memory

## Purpose

Goal 11B persists provider health and data-quality snapshots in SQLite so reports, alerts, workspace summaries, and provider watchlist items can consume historical caveats.

## Main functions

- `store_provider_health_snapshot()`
- `list_provider_health_snapshots()`
- `get_latest_provider_health_snapshot()`
- `store_data_quality_snapshot()`
- `list_data_quality_snapshots()`
- `get_latest_data_quality_snapshot()`
- `build_provider_report_memory()`
- `build_data_quality_report_memory()`

## Behavior

Provider watchlist items link to stored provider snapshots by symbol/display name/alias. Provider Health Report and Data Quality Report read stored snapshots and show gaps. Provider freshness alert conditions can evaluate from stored snapshot context.

## Tests

Covered by `tests/test_goal11b_provider_snapshot_memory.py`.


## Research-only policy

This system is for monitoring, inspection, documentation, and research workflow only. It does not perform broker execution, order routing, automatic rebalancing, or trade approval. External widgets are visual supplements only and are never used for calculations, reports, tests, backtests, provider health, or source-freshness scoring.

## Source and caveat policy

Every workflow must label source status, freshness, confidence, and gaps where available. Missing context remains `unavailable`, `missing`, `proxy`, `estimated`, `historical-only`, or `missing-key`; Goal 11B does not fill gaps with random values.
