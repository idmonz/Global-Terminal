# Visual Command Terminal Upgrade Plan

## Intent

Upgrade the existing Global Market Analyst Terminal with denser command-center visuals, stronger news intelligence layouts, and testable visual/data builders. This is an enhancement pass, not a rewrite.

## Guardrails

- Preserve restored market data, heatmaps, crypto intelligence, equity, energy, risk, and AI provider logic.
- Do not import runtime code from `external/worldmonitor-main/`.
- Do not present estimated data as real.
- Do not claim live AIS, dealer-confirmed gamma exposure, or official intelligence scoring without providers.
- Keep AI summaries button-triggered and neutral.

## Work Sequence

1. Verify baseline smoke tests, full pytest, canonical functions, and static universe row counts.
2. Fix release hygiene and document WorldMonitor as reference-only.
3. Add terminal UI helpers and source freshness builders.
4. Add news intelligence normalization, impact matrices, event timelines, and source panels.
5. Add market radar, signal fusion, hotspot scoring, and event clustering builders.
6. Extend map visualization with event, chokepoint, timeline, severity, and freshness charts.
7. Upgrade Overview, News, Stock Analyzer, Crypto Intelligence, and Screener pages.
8. Add offline tests for new visual/data builders.
9. Update docs and final validation report.

## Acceptance Focus

- Overview feels like a cross-asset command center.
- News is card/map/timeline based instead of table-first.
- Source freshness, severity, and data-gap labels are visible.
- Heuristic and proxy systems are labeled.
- Full tests and smoke checks pass after changes.
