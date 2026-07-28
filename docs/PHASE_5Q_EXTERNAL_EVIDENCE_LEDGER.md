# Phase 5Q External Evidence Ledger

Updated: 2026-06-23

## Mechanical Audit

The preflight audit covered 22 archives, 45,996 files, 35,193 text candidates, 9,561,357 counted text lines and 221,593 indexed symbols with zero read errors. This is mechanical inventory, not manual line-by-line semantic adoption.

## Semantically Used References

| Reference | License / boundary | Behavior adopted | Material rejected |
|---|---|---|---|
| `agent-skills-main.zip` | Process reference only | Goal-scoped phase execution, skill-like checklists, evidence-first closeout | No runtime code, no skill source vendored into the product |
| WorldMonitor daily-brief plans and source-history notes | AGPL / behavior-only | Source-filter discipline, brief relevance, local telemetry, conservative filtering, explicit stale/upstream gaps | No source, CSS, prompts, assets or data copied |
| OpenBB Workspace docs | External product docs / behavior-only | Widget as a self-contained analytical unit with data, visualization and interactivity | No OpenBB source copied; no AGPL platform code vendored |
| Bloomberg Terminal product pages | Public product behavior | Dense customized workspace with monitors, charting and market-moving news | No proprietary workflow, assets, data or branding copied |
| Koyfin product pages | Public product behavior | Market dashboard, watchlist, portfolio and report expectations | No assets, content, data or UI copied |
| TradingView feature docs | Public product behavior | Watchlist-driven alerts, symbol details/news/chart expectations | No charts, Pine, assets, data or proprietary UI copied |
| `TradingAgents-main.zip` | Apache-2.0 in archive; clean-room reference this phase | Multi-role analyst/research/risk workflow, structured-output validation, checkpoint/memory concepts, provider readiness tests | No trading action, order proposal, target/stop/sizing, assets, screenshots, LangGraph runtime or source copied |

## Clean-Room Implementation

Native files implementing the Phase 5Q behavior:

- `lib/daily_briefing.py`
- `lib/research_workspace_schema.py`
- `lib/api_contracts.py`
- `backend/api/app.py`
- `scripts/export_api_fixtures.py`
- `apps/web/src/components/DailyBriefWorkspace.tsx`
- `apps/web/src/app/page.tsx`
- `apps/web/src/lib/contracts.ts`
- `apps/web/src/lib/fixtures.ts`
- `apps/web/scripts/capture-phase5q.mjs`
- `tests/test_phase5q_daily_brief.py`
- `tests/test_phase5q_release_hygiene.py`

## Closeout Rule

Future Phase 5R may inspect external brief, widget, dashboard and map references, but adoption must remain behavior-first unless an exact permissive file path and notice review are documented.

See also `docs/PHASE_5Q_TRADINGAGENTS_ADOPTION_RESEARCH.md`.
