from __future__ import annotations
from typing import Any
from .report_sections import section, bullet_rows, inspect_next
from .report_models import REPORT_CAVEAT
from .provider_report_memory import build_provider_report_memory, build_data_quality_report_memory
from .report_source_snapshots import build_provider_gap_lines


def _watch_rows(context): return (context.get("watchlist") or {}).get("table") or []
def _events(context): return context.get("linked_events") or (context.get("watchlist") or {}).get("bundle", {}).get("events", {}).get("matches", [])
def _alerts(context): return context.get("alert_events") or []
def _commits(context): return context.get("strategy_commits") or []


def render_type_specific_markdown(context: dict[str, Any], title: str) -> str:
    report_type = context.get("report_type", "Research Report")
    provider_memory = context.get("provider_memory") or build_provider_report_memory(db_path=context.get("db_path"))
    dq_memory = context.get("data_quality_memory") or build_data_quality_report_memory(db_path=context.get("db_path"))
    parts = [f"# {title}", "", f"> {REPORT_CAVEAT}", "", f"Generated at: `{context.get('generated_at', 'manual')}`", ""]
    if report_type == "Watchlist Brief":
        parts.append(section("Watchlist Changes And Context", bullet_rows(_watch_rows(context), ["symbol", "type", "source_status", "freshness", "latest_value", "change_pct"], empty="No watchlist rows available.")))
        parts.append(section("Linked Events", [f"- {m.get('display_name')} matched `{m.get('event',{}).get('title')}` labels `{m.get('labels')}` confidence `{m.get('confidence_score')}`" for m in _events(context)[:10]] or ["- No linked events supplied."]))
        parts.append(section("Active Alerts", bullet_rows(_alerts(context), ["metric", "status", "severity", "message"], empty="No alert events available.")))
        parts.append(inspect_next(["WATCHLIST", "EVALUATE ALERTS", "GENERATE PROVIDER REPORT"]))
    elif report_type == "Provider Health Report":
        parts.append(section("Provider Snapshot Memory", [f"- snapshots: {provider_memory.get('snapshot_count')} | gaps: {provider_memory.get('gap_count')} | latest status: {provider_memory.get('status')}"]))
        parts.append(section("Provider And Data Caveats", build_provider_gap_lines(provider_memory, dq_memory)))
        parts.append(inspect_next(["DATA PROBE", "PROVIDER REPORT", "DATA QUALITY REPORT"]))
    elif report_type == "Data Quality Report":
        parts.append(section("Data Quality Snapshot Memory", [f"- snapshots: {dq_memory.get('snapshot_count')} | gaps: {dq_memory.get('gap_count')} | latest status: {dq_memory.get('status')}"]))
        parts.append(section("Gaps By Scope", build_provider_gap_lines(provider_memory, dq_memory)))
        parts.append(inspect_next(["DATA QUALITY REPORT", "WORKSPACE"]))
    elif report_type == "Strategy Review Report":
        parts.append(section("Recent Strategy Commits", bullet_rows(_commits(context), ["commit_id", "strategy_id", "status", "message"], empty="No strategy commits available.")))
        warnings=[]
        for c in _commits(context):
            for g in c.get("guard_results_json", []) or []:
                if g.get("status") != "passed": warnings.append(f"- `{c.get('commit_id')}` guard `{g.get('guard')}` status `{g.get('status')}`: {g.get('message')}")
        parts.append(section("Guard Warnings", warnings or ["- No guard warnings in supplied context."]))
        parts.append(inspect_next(["STRATEGY LOG", "GENERATE STRATEGY REVIEW"]))
    elif report_type == "War Room Brief":
        parts.append(section("Event Clusters", [f"- `{m.get('event',{}).get('title')}` affected `{m.get('display_name')}` labels `{m.get('labels')}`" for m in _events(context)[:15]] or ["- No OSINT events supplied."]))
        parts.append(inspect_next(["GLOBAL WAR", "GENERATE WAR ROOM BRIEF"]))
    elif report_type == "Energy Geopolitics Brief":
        parts.append(section("Energy And Chokepoint Context", [f"- `{m.get('event',{}).get('title')}` linked to `{m.get('display_name')}` confidence `{m.get('confidence_score')}`" for m in _events(context)[:15]] or ["- No energy/chokepoint event context supplied."]))
        parts.append(inspect_next(["CL ENERGY", "GLOBAL WAR"]))
    elif report_type == "Crypto Derivatives Watch":
        parts.append(section("Crypto Context", bullet_rows(_watch_rows(context), ["symbol", "source_status", "freshness", "latest_value", "crypto_funding", "crypto_open_interest"], empty="No crypto rows supplied.")))
        parts.append(inspect_next(["BTC CRYPTO", "WATCHLIST"]))
    elif report_type == "Alert Summary Report":
        parts.append(section("Alert Timeline", bullet_rows(_alerts(context), ["metric", "status", "severity", "message"], empty="No alert events available.")))
        parts.append(inspect_next(["ALERTS", "EVALUATE ALERTS"]))
    else:
        parts.append(section("Daily Global Workspace Snapshot", [f"- Watchlist items: {len(_watch_rows(context))}", f"- Alert events: {len(_alerts(context))}", f"- Strategy commits: {len(_commits(context))}", f"- Provider gaps: {provider_memory.get('gap_count', 0)}", f"- Data quality gaps: {dq_memory.get('gap_count', 0)}"]))
        parts.append(inspect_next(["WORKSPACE", "WATCHLIST", "REPORTS", "STRATEGY LOG"]))
    parts.append(section("Source Snapshot", [f"- `{context.get('source_snapshot', {})}`"]))
    parts.append(section("Provider Gaps", build_provider_gap_lines(provider_memory, dq_memory)))
    return "\n".join(parts).strip() + "\n"
