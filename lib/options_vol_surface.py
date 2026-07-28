from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .options_chain_schema import GOAL12B_RESEARCH_ONLY_NOTICE
from .options_surface_quality import build_surface_quality_score, build_surface_anomaly_table


def _parse_expiry_days(expiry: str, timestamp: str | None = None) -> int | None:
    try:
        exp = datetime.fromisoformat(str(expiry)).replace(tzinfo=timezone.utc)
    except Exception:
        try:
            exp = datetime.strptime(str(expiry), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None
    base = None
    if timestamp:
        try:
            base = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
        except Exception:
            base = None
    base = base or datetime.now(timezone.utc)
    return max(0, (exp - base).days)


def build_vol_surface_snapshot(iv_snapshot: dict[str, Any]) -> dict[str, Any]:
    points = []
    for row in iv_snapshot.get("rows", []):
        iv = row.get("mid_iv") if row.get("mid_iv") is not None else row.get("implied_volatility")
        if iv is None:
            continue
        try:
            s = float(row.get("underlying_price")); k = float(row.get("strike"))
            moneyness = k / s if s > 0 else None
        except Exception:
            continue
        points.append({
            "expiry": str(row.get("expiry", "")),
            "days_to_expiry": _parse_expiry_days(str(row.get("expiry", "")), row.get("timestamp")),
            "strike": k,
            "moneyness": moneyness,
            "option_type": row.get("option_type", ""),
            "mid_iv": float(iv),
            "mid_price": row.get("mid"),
            "bid": row.get("bid"),
            "ask": row.get("ask"),
            "mark": row.get("mark"),
            "last": row.get("last"),
            "time_to_expiry_years": row.get("time_to_expiry_years"),
            "underlying_price": row.get("underlying_price"),
            "futures_price": row.get("futures_price"),
            "risk_free_rate": row.get("risk_free_rate"),
            "dividend_yield": row.get("dividend_yield"),
            "domestic_rate": row.get("domestic_rate"),
            "foreign_rate": row.get("foreign_rate"),
            "bid_iv": row.get("bid_iv"),
            "ask_iv": row.get("ask_iv"),
            "source": row.get("source", "user_supplied_csv"),
            "freshness": iv_snapshot.get("source_snapshot", {}).get("freshness", "unknown"),
            "spread_pct": row.get("spread_pct"),
            "pricing_model": row.get("pricing_model", row.get("model")),
            "iv_status": row.get("iv_status", "supplied_or_solved"),
            "interpolated": False,
            "research_only": True,
        })
    quality = summarize_surface_quality(points)
    surface = {"ok": True, "surface_id": iv_snapshot.get("snapshot_id", "iv_snapshot") + "_surface", "points": points, "point_count": len(points), "quality": quality, "source_snapshot": iv_snapshot.get("source_snapshot", {}), "notice": GOAL12B_RESEARCH_ONLY_NOTICE, "research_only": True}
    surface["quality_score"] = build_surface_quality_score(surface)
    surface["anomaly_table"] = build_surface_anomaly_table(surface)
    return surface


def build_smile_table(surface_snapshot: dict[str, Any], expiry: str | None = None) -> list[dict[str, Any]]:
    rows = [p for p in surface_snapshot.get("points", []) if expiry is None or p.get("expiry") == expiry]
    return sorted([{"expiry": p["expiry"], "strike": p["strike"], "moneyness": p["moneyness"], "option_type": p["option_type"], "mid_iv": p["mid_iv"], "interpolated": p.get("interpolated", False)} for p in rows], key=lambda x: (x["expiry"], x["strike"], x["option_type"]))


def build_skew_table(surface_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    by_expiry: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in surface_snapshot.get("points", []):
        by_expiry[p["expiry"]].append(p)
    out = []
    for expiry, rows in by_expiry.items():
        puts = [p for p in rows if p.get("option_type") == "put"]
        calls = [p for p in rows if p.get("option_type") == "call"]
        put_iv = min(puts, key=lambda p: abs((p.get("moneyness") or 0) - 0.95))["mid_iv"] if puts else None
        call_iv = min(calls, key=lambda p: abs((p.get("moneyness") or 0) - 1.05))["mid_iv"] if calls else None
        out.append({"expiry": expiry, "put_95_moneyness_iv": put_iv, "call_105_moneyness_iv": call_iv, "skew_put_minus_call": None if put_iv is None or call_iv is None else put_iv - call_iv, "research_only": True})
    return sorted(out, key=lambda x: x["expiry"])


def build_term_structure_table(surface_snapshot: dict[str, Any], *, moneyness_target: float = 1.0) -> list[dict[str, Any]]:
    by_expiry: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in surface_snapshot.get("points", []):
        by_expiry[p["expiry"]].append(p)
    out = []
    for expiry, rows in by_expiry.items():
        nearest = min(rows, key=lambda p: abs((p.get("moneyness") or 0) - moneyness_target))
        out.append({"expiry": expiry, "days_to_expiry": nearest.get("days_to_expiry"), "nearest_moneyness": nearest.get("moneyness"), "mid_iv": nearest.get("mid_iv"), "research_only": True})
    return sorted(out, key=lambda x: (x.get("days_to_expiry") is None, x.get("days_to_expiry") or 10**9))


def interpolate_surface_grid_nearest_safe(surface_snapshot: dict[str, Any], expiries: list[str], strikes: list[float]) -> dict[str, Any]:
    points = surface_snapshot.get("points", [])
    grid = []
    for expiry in expiries:
        candidates = [p for p in points if p.get("expiry") == expiry]
        for strike in strikes:
            if not candidates:
                grid.append({"expiry": expiry, "strike": float(strike), "mid_iv": None, "interpolated": False, "reason": "no_expiry_points"})
            else:
                nearest = min(candidates, key=lambda p: abs(float(p["strike"]) - float(strike)))
                grid.append({"expiry": expiry, "strike": float(strike), "mid_iv": nearest["mid_iv"], "nearest_source_strike": nearest["strike"], "interpolated": True, "method": "nearest_safe", "label": "interpolated_from_supplied_chain"})
    return {"ok": True, "grid": grid, "interpolation_label": "nearest_safe_supplied_points_only", "research_only": True}


def summarize_surface_quality(points_or_snapshot: list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
    points = points_or_snapshot.get("points", []) if isinstance(points_or_snapshot, dict) else points_or_snapshot
    expiries = {p.get("expiry") for p in points}
    strikes = {p.get("strike") for p in points}
    option_types = {p.get("option_type") for p in points}
    return {"point_count": len(points), "expiry_count": len(expiries), "strike_count": len(strikes), "option_types": sorted(str(v) for v in option_types if v), "caveats": ["supplied_chain_only", "not_a_volatility_forecast", "interpolation_labeled_when_used"], "research_only": True}


def build_surface_heatmap_payload(surface_snapshot: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "x": sorted({p["strike"] for p in surface_snapshot.get("points", [])}), "y": sorted({p["expiry"] for p in surface_snapshot.get("points", [])}), "points": surface_snapshot.get("points", []), "visual_label": "research_vol_surface_heatmap_supplied_chain_only", "research_only": True}
