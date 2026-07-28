from __future__ import annotations
from pathlib import Path
from typing import Any
from .report_context_builder import build_report_context, build_report_source_snapshot
from .report_inbox import create_report
from .report_renderer import render_report_markdown, render_report_html

REPORT_TYPE_META = {
    "daily": ("Daily Global Brief", "Daily Global Brief", "Manual daily workspace briefing with source caveats."),
    "watchlist": ("Watchlist Brief", "Watchlist Brief", "Watchlist changes, linked events, alert state, and provider caveats."),
    "war_room": ("War Room Brief", "War Room Brief", "OSINT event clusters, affected regions, and confidence labels."),
    "energy": ("Energy Geopolitics Brief", "Energy Geopolitics Brief", "Energy and chokepoint context with source caveats."),
    "crypto": ("Crypto Derivatives Watch", "Crypto Derivatives Watch", "Crypto funding/OI/liquidation context when supplied."),
    "portfolio": ("Portfolio Risk Report", "Portfolio Risk Report", "Portfolio risk context when supplied, with no allocation instruction."),
    "provider": ("Provider Health Report", "Provider Health Report", "Provider health, missing keys, stale sources, and setup caveats."),
    "data_quality": ("Data Quality Report", "Data Quality Report", "Data quality gaps, proxy labels, and freshness distribution."),
    "strategy": ("Strategy Review Report", "Strategy Review Report", "Strategy commit diffs, guard warnings, and tracking status."),
    "alerts": ("Alert Summary Report", "Alert Summary Report", "Triggered, skipped, deduped, cooldown, and expiry state."),
}


def generate_report_by_key(key: str, db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]:
    report_type, title, summary = REPORT_TYPE_META.get(key, REPORT_TYPE_META["daily"])
    context = build_report_context(report_type, db_path, **extra)
    markdown = render_report_markdown(context, title)
    html = render_report_html(context, title)
    return create_report(report_type=report_type, title=title, summary=summary, source_snapshot=build_report_source_snapshot(context), data_confidence=context.get("source_snapshot", {}).get("confidence", "available-data"), provider_gaps=context.get("provider_gaps", []), markdown_body=markdown, html_body_optional=html, linked_watchlist_items=[row.get("item_id") for row in context.get("watchlist", {}).get("items", []) if row.get("item_id")], linked_events=[m.get("event", {}).get("dedupe_key") for m in context.get("linked_events", []) if m.get("event")], linked_strategy_commits=[c.get("commit_id") for c in context.get("strategy_commits", []) if c.get("commit_id")], tags=[key, "goal11b"], db_path=db_path)


def generate_daily_global_brief(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("daily", db_path, **extra)
def generate_watchlist_brief(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("watchlist", db_path, **extra)
def generate_war_room_brief(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("war_room", db_path, **extra)
def generate_energy_geopolitics_brief(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("energy", db_path, **extra)
def generate_crypto_derivatives_watch(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("crypto", db_path, **extra)
def generate_portfolio_risk_report(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("portfolio", db_path, **extra)
def generate_provider_health_report(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("provider", db_path, **extra)
def generate_data_quality_report(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("data_quality", db_path, **extra)
def generate_strategy_review_report(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("strategy", db_path, **extra)
def generate_alert_summary_report(db_path: str | Path | None = None, **extra: Any) -> dict[str, Any]: return generate_report_by_key("alerts", db_path, **extra)
