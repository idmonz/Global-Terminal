from __future__ import annotations
from pathlib import Path
from typing import Any
from .watchlist_store import get_watchlist_item
from .watchlist_data_enricher import enrich_watchlist_item


def resolve_alert_metric(rule: dict[str, Any], data_context: dict[str, Any] | None = None, *, db_path: str | Path | None = None) -> dict[str, Any]:
    ctx = dict(data_context or {})
    metric = rule.get("metric")
    watch_item_id = rule.get("watch_item_id")
    if watch_item_id and watch_item_id in ctx and isinstance(ctx[watch_item_id], dict):
        ctx = {**ctx, **ctx[watch_item_id]}
    item = get_watchlist_item(watch_item_id, db_path) if watch_item_id else None
    if item:
        enriched = enrich_watchlist_item(item, supplied_context=ctx, db_path=db_path)
        ctx = {**enriched, **ctx}
    observed = ctx.get(metric)
    if observed is None and metric == "provider_health":
        observed = ctx.get("source_status") or ctx.get("status")
    if observed is None and metric == "source_freshness":
        observed = ctx.get("freshness")
    if observed is None and metric == "data_quality":
        observed = ctx.get("data_confidence") or ctx.get("confidence")
    return {"metric": metric, "observed_value": observed, "context": ctx, "source_snapshot": ctx.get("source_snapshot") or {"freshness": ctx.get("freshness", "unknown"), "confidence": ctx.get("data_confidence", "unknown"), "source_status": ctx.get("source_status", "unknown")}, "data_confidence": ctx.get("data_confidence", "unknown")}
