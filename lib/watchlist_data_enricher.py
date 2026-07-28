from __future__ import annotations
from pathlib import Path
from typing import Any
from .watchlist_context_router import route_watchlist_item, default_source_state
from .watchlist_provider_context import build_provider_context
from .osint_entity_matcher import match_events_to_items


def _norm_symbol(item: dict[str, Any]) -> str:
    return str(item.get("symbol") or item.get("display_name") or "").upper()


def _lookup_market(item: dict[str, Any], supplied_market: dict[str, Any] | list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    symbol = _norm_symbol(item)
    if isinstance(supplied_market, dict):
        if symbol in {str(k).upper() for k in supplied_market.keys()}:
            for k, v in supplied_market.items():
                if str(k).upper() == symbol:
                    return dict(v) if isinstance(v, dict) else {"latest_value": v}
        rows = supplied_market.get("rows") or supplied_market.get("market_rows")
        if rows:
            return _lookup_market(item, rows)
    if isinstance(supplied_market, list):
        for row in supplied_market:
            key = str(row.get("symbol") or row.get("ticker") or row.get("label") or "").upper()
            if key == symbol:
                return dict(row)
    return None


def _market_context(item: dict[str, Any], supplied_context: dict[str, Any] | None = None) -> dict[str, Any]:
    supplied_context = supplied_context or {}
    row = _lookup_market(item, supplied_context.get("market") or supplied_context.get("market_rows") or supplied_context.get("quotes"))
    if not row:
        return {"source_status": "unavailable", "freshness": "unavailable", "data_confidence": "missing", "latest_value": None, "change_pct": None, "market_context_status": "missing"}
    return {
        "source_status": row.get("source_status") or row.get("status") or "available",
        "freshness": row.get("freshness") or row.get("data_freshness") or "supplied",
        "data_confidence": row.get("data_confidence") or row.get("confidence") or "supplied",
        "latest_value": row.get("latest_value", row.get("price", row.get("close", row.get("last")))),
        "change_pct": row.get("change_pct", row.get("daily_return", row.get("return_1d_pct"))),
        "realized_volatility_pct": row.get("realized_volatility_pct", row.get("realized_vol", row.get("volatility"))),
        "drawdown_pct": row.get("drawdown_pct", row.get("drawdown_52w")),
        "source": row.get("source", "supplied-market-context"),
        "market_row": row,
    }


def _osint_context(item: dict[str, Any], supplied_context: dict[str, Any] | None = None) -> dict[str, Any]:
    events = (supplied_context or {}).get("events") or (supplied_context or {}).get("osint_events") or []
    matches = match_events_to_items(events, [item]) if events else []
    top = matches[0] if matches else None
    return {"linked_event_count": len(matches), "linked_events": matches, "source_status": "available" if matches else "unavailable", "freshness": (top or {}).get("freshness", "unavailable"), "data_confidence": "event-linked" if matches else "missing", "event_severity": max([float(m.get("event", {}).get("severity", 0) or 0) for m in matches] or [0])}


def _strategy_context(item: dict[str, Any], supplied_context: dict[str, Any] | None = None) -> dict[str, Any]:
    strategy_id = item.get("symbol") or item.get("display_name")
    rows = (supplied_context or {}).get("strategies") or (supplied_context or {}).get("strategy_commits") or []
    matched = [r for r in rows if str(r.get("strategy_id") or r.get("symbol") or r.get("display_name")) == str(strategy_id)]
    latest = matched[0] if matched else None
    guard_results = (latest or {}).get("guard_results_json") or (latest or {}).get("guard_results") or []
    warnings = sum(1 for g in guard_results if str(g.get("status")) != "passed") if isinstance(guard_results, list) else 0
    return {"source_status": "available" if latest else "unavailable", "freshness": "local" if latest else "unavailable", "data_confidence": "local" if latest else "missing", "strategy_snapshot": latest, "guard_warning_count": warnings}


def enrich_watchlist_item(item: dict[str, Any], *, supplied_context: dict[str, Any] | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    route = route_watchlist_item(item)
    base = {**item, **default_source_state(route), "linked_event_count": 0, "active_alert_count": 0, "linked_report_count": 0}
    if route == "market":
        base.update(_market_context(item, supplied_context))
        if item.get("item_type") == "crypto":
            crypto_ctx = (supplied_context or {}).get("crypto", {}).get(_norm_symbol(item), {}) if isinstance((supplied_context or {}).get("crypto"), dict) else {}
            base.update({f"crypto_{k}": v for k, v in crypto_ctx.items()})
    elif route == "osint" or route == "event_theme":
        base.update(_osint_context(item, supplied_context))
    elif route == "provider":
        base.update(build_provider_context(item, db_path=db_path, supplied=(supplied_context or {}).get("providers")))
    elif route == "strategy":
        base.update(_strategy_context(item, supplied_context))
    return base


def enrich_watchlist_items(items: list[dict[str, Any]], *, supplied_context: dict[str, Any] | None = None, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    return [enrich_watchlist_item(item, supplied_context=supplied_context, db_path=db_path) for item in items or []]


def build_watchlist_context_bundle(items: list[dict[str, Any]], *, supplied_context: dict[str, Any] | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    enriched = enrich_watchlist_items(items, supplied_context=supplied_context, db_path=db_path)
    return {"items": enriched, "market": build_watchlist_market_snapshot(enriched), "risk": build_watchlist_risk_snapshot(enriched), "events": build_watchlist_event_snapshot(enriched), "providers": build_watchlist_provider_snapshot(enriched), "strategies": build_watchlist_strategy_snapshot(enriched)}


def build_watchlist_market_snapshot(enriched_items: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [i for i in enriched_items if i.get("route") == "market"]
    return {"rows": rows, "available_count": sum(1 for r in rows if r.get("latest_value") is not None), "missing_count": sum(1 for r in rows if r.get("latest_value") is None)}


def build_watchlist_risk_snapshot(enriched_items: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [i for i in enriched_items if i.get("realized_volatility_pct") is not None or i.get("event_severity")]
    return {"rows": rows, "requires_review_count": sum(1 for r in rows if str(r.get("source_status")) in {"stale", "missing_key", "unavailable"} or float(r.get("event_severity") or 0) >= 7)}


def build_watchlist_event_snapshot(enriched_items: list[dict[str, Any]]) -> dict[str, Any]:
    matches = []
    for item in enriched_items:
        matches.extend(item.get("linked_events") or [])
    return {"matches": matches, "match_count": len(matches), "low_confidence_count": sum(1 for m in matches if m.get("timeline_only"))}


def build_watchlist_provider_snapshot(enriched_items: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [i for i in enriched_items if i.get("route") == "provider"]
    return {"rows": rows, "gap_count": sum(1 for r in rows if r.get("missing_keys") or str(r.get("source_status")) in {"missing_key", "error", "stale", "unavailable"})}


def build_watchlist_strategy_snapshot(enriched_items: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [i for i in enriched_items if i.get("route") == "strategy"]
    return {"rows": rows, "guard_warning_count": sum(int(r.get("guard_warning_count") or 0) for r in rows)}
