from __future__ import annotations
from typing import Any
from .workspace_event_linker import build_watchlist_osint_context


def build_osint_report_context(events: list[dict[str, Any]], watchlist_items: list[dict[str, Any]]) -> dict[str, Any]:
    ctx = build_watchlist_osint_context(events, watchlist_items)
    ctx["report_labels"] = ["source/freshness/confidence required", "inferred events labeled"]
    return ctx

