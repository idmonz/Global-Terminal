# Phase 5L Preflight Report

Updated: 2026-06-22

## Verdict

Phase 5L is an adoption and product-integration phase, not a greenfield storage project. The repository already contains a mature local-first research substrate:

- SQLite paths, schema, migrations, backup, import and export;
- workspace profile, activity log, watchlist CRUD and alert/report stores;
- report reader, review, source snapshots and safe HTML/Markdown export;
- research guards, attachments, artifacts and event-to-watchlist linking;
- Streamlit Research Workspace, Watchlist & Alerts, Report Inbox and Tool Center.

The commercial Next.js product lacked one coherent save, find, revisit, compare and export journey. Phase 5L therefore adds a thin domain contract and web workflow over the existing storage boundary.

## Baseline

- Phase 5K full Python/web/release gates were green.
- `/?view=research-memory` had no dedicated product route and fell through to contract diagnostics.
- No Research Memory fixture, API descriptor, FastAPI route or product navigation entry existed.
- Existing private storage root is `data/private`; release policy excludes it.

## Reuse Decision

Reuse `research_workspace_*`, `watchlist_store`, `report_inbox`, `report_source_snapshots`, `research_guard_pipeline` and private export paths. Add only:

1. additive schema v4 tables for memory metadata/private bodies and append-only source history;
2. `lib/research_memory.py` normalization, CRUD, compatibility, search and sanitized export;
3. API/fixture and commercial web adoption.

## Baseline Risks

- private query text must use POST bodies, never query strings;
- local API data is private and must never become a static fixture or release screenshot;
- source failure must append a new observation, never mutate earlier live history;
- malformed/corrupt stores must return an explicit unavailable state;
- full private exports remain explicit local actions outside release artifacts.

