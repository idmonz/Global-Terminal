# Goal 11 Spec — Personal Research Operating System

## Objective

Build a daily-usable personal research workflow layer on top of the Goal 10B baseline.

## Scope

- Local SQLite research workspace storage.
- Personal Research Workspace page.
- Multi-domain watchlist and alert center.
- Report inbox and manual report generators.
- Strategy-as-Git research decision log.
- OSINT-aware watchlist briefing and report context.
- Command palette and quick actions.
- Optional TradingView visual supplement.
- Future attachment hooks for Options / Quant Model Lab.
- Agent-skills-inspired governance docs and gates.

## Non-goals

No rewrite, source reset, frontend migration, MongoDB/Auth migration, email automation, background daemon, full MCP/API server, full Options Lab, full Quant Model Library, live trading, broker execution, order routing, external plugin installation, or paid-provider requirement.

## Data model

SQLite tables: workspace_profile, watchlist_items, alert_rules, alert_events, report_inbox_items, strategy_commits, strategy_artifacts, provider_health_snapshots, data_quality_snapshots, command_history, workspace_activity_log.

## Pages

- `pages/19_Research_Workspace.py`
- `pages/20_Watchlist_Alerts.py`
- `pages/21_Report_Inbox.py`
- `pages/22_Strategy_Decision_Log.py`

## Security constraints

- Private DB and exports under `data/private/`.
- No API keys stored in workspace DB.
- No full secrets displayed.
- External folders and archives excluded from release.
- TradingView optional only and never used for calculations.
- Research-only disclaimers on workspace/watchlist/report/strategy pages.

## Acceptance criteria

Acceptance criteria are defined by the user Goal 11 prompt and implemented through storage, workspace, watchlist, alert, report, strategy, OSINT, command, compliance, test, and release-hygiene modules.

