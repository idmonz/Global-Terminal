from __future__ import annotations
from pathlib import Path
from typing import Any
from .watchlist_engine import build_watchlist_context, build_watchlist_heatmap_payload, build_watchlist_rmi_payload, build_watchlist_volatility_payload
from .alert_store import list_alert_rules, list_alert_events
from .alert_visuals import build_alert_summary_cards, build_alert_timeline
from .watchlist_action_cards import build_watchlist_action_cards
from .watchlist_news_event_grid import build_watchlist_news_event_grid
from .watchlist_detail_panel import build_watchlist_detail_panel
from .watchlist_alert_builder_ui import build_watchlist_alert_builder_payload
from .watchlist_table_columns import build_watchlist_table_columns
from .source_freshness_strip import build_source_freshness_strip


def build_watchlist_page_payload(db_path: str | Path | None = None, *, supplied_context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = build_watchlist_context(db_path, supplied_context=supplied_context)
    rules = list_alert_rules(db_path=db_path)
    events = list_alert_events(db_path=db_path)
    related_events = context.get("bundle", {}).get("events", {}).get("matches", [])
    product_table = build_watchlist_table_columns(context["table"])
    selected = (context.get("enriched_items") or context.get("items") or [{}])[0] if context.get("summary", {}).get("count", 0) else {}
    source_rows = [{"source": row.get("source") or row.get("name") or row.get("symbol"), "freshness": row.get("freshness") or row.get("source_status"), "confidence": row.get("data_confidence")} for row in context["table"]]
    return {
        "summary": context["summary"],
        "summary_strip": [{"label": "tracked", "value": context["summary"].get("count", 0)}, {"label": "alerts", "value": len(rules)}, {"label": "events", "value": len(related_events)}],
        "source_freshness": build_source_freshness_strip(source_rows, title="Watchlist source freshness"),
        "action_cards": build_watchlist_action_cards(context["summary"]),
        "table": context["table"],
        "product_table": product_table,
        "detail_panel": build_watchlist_detail_panel(selected, events=related_events),
        "news_event_grid": build_watchlist_news_event_grid(related_events),
        "alert_builder": build_watchlist_alert_builder_payload(selected),
        "heatmap": build_watchlist_heatmap_payload(db_path, supplied_context=supplied_context),
        "rmi": build_watchlist_rmi_payload(db_path, supplied_context=supplied_context),
        "volatility": build_watchlist_volatility_payload(db_path, supplied_context=supplied_context),
        "related_events": related_events,
        "alert_cards": build_alert_summary_cards(rules, events),
        "alert_timeline": build_alert_timeline(events),
        "empty_states": {"no_watchlist_items": context["summary"].get("count", 0) == 0, "no_alerts": len(rules) == 0, "no_events": len(events) == 0},
        "raw_payload_available": True,
        "research_only": True,
    }
