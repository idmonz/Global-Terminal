# Report Inbox System

## Purpose

Report Inbox stores manually generated research reports with source snapshots, provider gaps, linked watchlist items, linked events, linked strategy commits, markdown body, and safe HTML body.

## V2 report types

- Daily Global Brief
- Watchlist Brief
- War Room Brief
- Energy Geopolitics Brief
- Crypto Derivatives Watch
- Portfolio Risk Report
- Provider Health Report
- Data Quality Report
- Strategy Review Report
- Alert Summary Report

Each report now uses type-specific sections rather than a generic count-only body.

## Main functions

- `generate_report_by_key()`
- `render_type_specific_markdown()`
- `render_safe_report_html()`
- `build_report_source_snapshot()`
- `build_report_inbox_page_payload()`

## Export safety

HTML output escapes user-supplied strings and does not load external scripts by default.

## Tests

Covered by `tests/test_goal11b_report_content_quality.py`.


## Research-only policy

This system is for monitoring, inspection, documentation, and research workflow only. It does not perform broker execution, order routing, automatic rebalancing, or trade approval. External widgets are visual supplements only and are never used for calculations, reports, tests, backtests, provider health, or source-freshness scoring.

## Source and caveat policy

Every workflow must label source status, freshness, confidence, and gaps where available. Missing context remains `unavailable`, `missing`, `proxy`, `estimated`, `historical-only`, or `missing-key`; Goal 11B does not fill gaps with random values.

## Goal 11C Productization Update

Goal 11C adds product-quality Research OS UX: shared visual payloads, source freshness chips, command palette state, watchlist action cards/detail/event grid, report reader/review workflow, strategy review queue/artifact timeline, Intel Feed/Live Alerts/View Presets/Layer Panel, Research Tool Center, deeper tests, and release hygiene docs. External projects were inspected as conceptual references only; no external source code was copied or vendored.
