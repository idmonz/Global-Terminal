# Goal 11B Gap Audit

Goal 11 is a working MVP, but the following exact files/functions require hardening before the system is daily-usable.

## 1. Lightweight UI wrappers

- `pages/19_Research_Workspace.py`: shows metric cards and raw `payload["summary"]` JSON. Needs structured tabs, empty states, activity, provider/data quality caveats, and click-next cards.
- `pages/20_Watchlist_Alerts.py`: uses raw `st.json()` for heatmap/RMI/volatility. Needs enriched context panels, alert editor, evaluation state, timeline, and raw expanders only.
- `pages/21_Report_Inbox.py`: only generator selector, table, and latest markdown. Needs filters, cards, detail viewer, source snapshot, provider gaps, exports.
- `pages/22_Strategy_Decision_Log.py`: only create form, dataframe, guard JSON. Needs diff view, timeline graph, guard cards, linked artifacts, forward tracking.

## 2. Metadata-only watchlist payloads

- `lib/watchlist_engine.py::build_watchlist_heatmap_payload`: always emits `value: 1` and `freshness: local`.
- `lib/watchlist_engine.py::build_watchlist_rmi_payload`: always emits `relative_state: requires review`.
- `lib/watchlist_engine.py::build_watchlist_volatility_payload`: always emits unavailable rows.
- `lib/watchlist_market_context.py`: needs route-specific market/provider/OSINT/strategy context composition.
- Required improvements: `watchlist_context_router`, `watchlist_data_enricher`, `watchlist_alias_registry`, heatmap/RMI/volatility adapters.

## 3. Thin alert evaluation

- `lib/alert_evaluator.py::evaluate_alert_rule`: no durable previous value, cooldown, expiry, dedupe, or context resolver.
- `lib/alert_store.py`: event rows do not expose transition/dedupe metadata as first-class fields.
- Required improvements: `alert_metric_resolver`, `alert_state_machine`, `alert_deduper`, `alert_context_router`.

## 4. Generic report generator

- `lib/scheduled_briefing_engine.py::_generate`: all reports share one thin body.
- `lib/report_renderer.py::render_report_markdown`: workspace counts only.
- Required improvements: type-specific report generators, sections, source snapshots, quality checks, HTML escaping.

## 5. Placeholder guard pipeline

- `lib/research_guard_pipeline.py`: most guards pass with generic text even when metadata is missing.
- `lib/strategy_decision_log.py::compare_strategy_commits`: compares only a few fields.
- Required improvements: real guard rule inspection, commit diff, graph, review queue, forward metrics.

## 6. Duplicate OSINT matching modules

- `lib/watchlist_event_matcher.py` and `lib/workspace_event_linker.py` duplicate token matching.
- Required improvements: alias registry, entity matcher, confidence scoring, dedupe, labels.

## 7. Weak provider snapshot consumption

- `provider_health_snapshots` and `data_quality_snapshots` exist in SQLite but report/alert/workspace consumers are thin.
- Required improvements: `provider_snapshot_store`, `data_quality_snapshot_store`, `provider_report_memory`.

## 8. Shallow tests

- Many Goal 11 tests assert module/function existence or minimal rows. Goal 11B must assert content, state transitions, event matching, provider snapshot usage, and release hygiene.

## 9. Shallow docs

- `docs/PERSONAL_RESEARCH_OPERATING_SYSTEM.md`, `docs/MULTI_DOMAIN_WATCHLIST_SYSTEM.md`, and related docs need real operating workflow, examples, caveats, tests, and limitations.

## 10. Missing Overview click-path integration

- `app.py` does not strongly expose Goal 11 counts/cards in the main overview.
- `lib/click_path_engine.py` partially links Research Workspace but needs Watchlist/Reports/Strategy cards.
- `lib/terminal_workspace_router.py`, `lib/top_command_bar.py`, `lib/research_command_palette.py`, and `lib/workspace_quick_actions.py` need deeper operational action payloads.

## 11. Regression risk versus Goal 10B

- Risk is moderate if Goal 11B imports heavy providers directly. Mitigation: adapters must accept supplied/mock context and use optional imports/fallbacks. No internet/API/OpenBB/Streamlit runtime required for tests.
