# Personal Research Operating System

Goal 11B turns the Personal Research OS into the main daily workflow layer over the existing market terminal.

## Purpose

The workspace answers: what is tracked, what changed, what requires review, which reports exist, which alert conditions were evaluated, which strategy research commits changed, and which provider/data-quality caveats affect the workspace.

## Data model

The workflow uses local SQLite tables for profile, watchlist, alert rules/events, reports, strategy commits/artifacts, provider snapshots, data-quality snapshots, command history, and activity logs. Private state lives under `data/private/` and is excluded from release packages.

## Main functions

- `build_workspace_page_payload()`
- `build_research_os_nav_cards()`
- `build_research_os_status_card()`
- `build_workspace_summary()`
- `run_quick_action()`

## Page behavior

`pages/19_Research_Workspace.py` now renders structured tabs for summary, quick actions, activity, and raw payload. Raw JSON is kept behind an explicit raw payload tab.

## Manual workflow

1. Open `WORKSPACE`.
2. Review counts and caveats.
3. Open Watchlist & Alerts, Report Inbox, or Strategy Decision Log from click-next cards.
4. Trigger report generation or alert evaluation manually.

## Tests

Covered by `tests/test_goal11b_workspace_page_payloads.py` and navigation regression tests.


## Research-only policy

This system is for monitoring, inspection, documentation, and research workflow only. It does not perform broker execution, order routing, automatic rebalancing, or trade approval. External widgets are visual supplements only and are never used for calculations, reports, tests, backtests, provider health, or source-freshness scoring.

## Source and caveat policy

Every workflow must label source status, freshness, confidence, and gaps where available. Missing context remains `unavailable`, `missing`, `proxy`, `estimated`, `historical-only`, or `missing-key`; Goal 11B does not fill gaps with random values.

## Goal 11C Productization Update

Goal 11C adds product-quality Research OS UX: shared visual payloads, source freshness chips, command palette state, watchlist action cards/detail/event grid, report reader/review workflow, strategy review queue/artifact timeline, Intel Feed/Live Alerts/View Presets/Layer Panel, Research Tool Center, deeper tests, and release hygiene docs. External projects were inspected as conceptual references only; no external source code was copied or vendored.
