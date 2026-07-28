from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_time(text: str) -> datetime | None:
    value = str(text or "").strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def label_option_chain_freshness(timestamp: str, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    parsed = _parse_time(timestamp)
    if parsed is None:
        return {"freshness": "unknown", "age_hours": None, "caveat": "timestamp_missing_or_unparseable", "research_only": True}
    age_hours = max(0.0, (now - parsed).total_seconds() / 3600.0)
    if age_hours <= 24:
        label = "fresh"
    elif age_hours <= 24 * 7:
        label = "stale"
    else:
        label = "historical"
    return {"freshness": label, "age_hours": age_hours, "timestamp": parsed.isoformat(), "caveat": "user_supplied_timestamp_preserved", "research_only": True}


def summarize_option_chain_quality(snapshot_or_rows: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(snapshot_or_rows, dict):
        rows = list(snapshot_or_rows.get("rows", snapshot_or_rows.get("accepted_rows", [])))
        rejected = list(snapshot_or_rows.get("rejected_rows", []))
        caveated = list(snapshot_or_rows.get("caveated_rows", []))
    else:
        rows = list(snapshot_or_rows)
        rejected = []
        caveated = []
    total = len(rows) + len(rejected)
    missing_source = sum(1 for r in rows if r.get("source") == "user_supplied_unknown_source")
    wide_spread = 0
    negative_or_crossed = 0
    timestamps = []
    for r in rows:
        bid = r.get("bid"); ask = r.get("ask")
        if bid is not None and ask is not None:
            try:
                bid_f, ask_f = float(bid), float(ask)
                if ask_f < bid_f:
                    negative_or_crossed += 1
                mid = (bid_f + ask_f) / 2.0
                if mid > 0 and (ask_f - bid_f) / mid > 0.25:
                    wide_spread += 1
            except Exception:
                negative_or_crossed += 1
        if r.get("timestamp"):
            timestamps.append(str(r.get("timestamp")))
    freshness_rows = [label_option_chain_freshness(ts) for ts in timestamps]
    freshness = "unknown"
    if freshness_rows:
        order = {"fresh": 0, "stale": 1, "historical": 2, "unknown": 3}
        freshness = max((row["freshness"] for row in freshness_rows), key=lambda x: order.get(x, 3))
    return {
        "total_rows": total,
        "accepted_rows": len(rows),
        "rejected_rows": len(rejected),
        "caveated_rows": len(caveated),
        "missing_source_rows": missing_source,
        "wide_spread_rows": wide_spread,
        "crossed_market_rows": negative_or_crossed,
        "freshness": freshness,
        "quality_score": 0.0 if total == 0 else max(0.0, 1.0 - (len(rejected) + wide_spread * 0.25 + missing_source * 0.1) / max(total, 1)),
        "caveats": ["supplied_csv_only", "no_live_option_chain_fetch", "freshness_from_user_supplied_timestamp"],
        "research_only": True,
    }
