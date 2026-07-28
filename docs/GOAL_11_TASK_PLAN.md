# Goal 11 Task Plan

| Task ID | Purpose | Files | Tests | Acceptance | Rollback note |
|---|---|---|---|---|---|
| G11-01 | Pre-flight and external research | docs/GOAL_11_PRE_FLIGHT_REPORT.md, GOAL_11_EXTERNAL_REFERENCE_RESEARCH_REPORT.md | quality gate tests | Baseline pass and boundaries documented | Docs-only rollback |
| G11-02 | Agent-skills governance | GOAL_11_AGENT_SKILLS_RESEARCH_REPORT.md, ENGINEERING_GOVERNANCE.md | governance tests | Reference-only process gates | Docs-only rollback |
| G11-03 | SQLite storage | lib/research_workspace_* | storage tests | Idempotent local DB, export/import | Remove new modules |
| G11-04 | Workspace | workspace modules, page 19 | workspace tests | Summary, profile, quick actions | Remove page/modules |
| G11-05 | Watchlist | watchlist modules, page 20 | watchlist tests | Multi-domain CRUD/context/import-export | Remove page/modules |
| G11-06 | Alerts | alert modules | alert tests | Manual evaluator, no false missing-data trigger | Remove modules |
| G11-07 | Reports | report modules, page 21 | report tests | Inbox, renderer, export, manual generators | Remove page/modules |
| G11-08 | Strategy-as-Git | strategy modules, page 22 | strategy tests | Research commits, guard pipeline, compare | Remove page/modules |
| G11-09 | OSINT linker | workspace_event_linker, osint_report_context, bridge | osint tests | Events/provider snapshots link to watchlist | Remove modules |
| G11-10 | Command palette | research_command_palette, quick_actions, router/registry updates | command tests | New commands route research-only | Revert router/registry patch |
| G11-11 | Future hooks | research_attachment_models | attachment tests | Lightweight schemas only | Remove module |
| G11-12 | Release/docs | release builder and docs | release/compliance tests | External/private/secrets excluded | Revert release token additions |

