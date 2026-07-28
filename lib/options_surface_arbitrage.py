from __future__ import annotations

from collections import defaultdict
from typing import Any

from .options_surface_price_checks import (
    build_price_based_surface_arbitrage_report,
    check_call_put_parity_residuals,
    check_call_vertical_price_monotonicity,
    check_calendar_price_monotonicity,
    check_option_price_convexity_by_strike,
    check_put_vertical_price_monotonicity,
)


def _group(points: list[dict[str, Any]], *keys: str) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for p in points:
        out[tuple(p.get(k) for k in keys)].append(p)
    return out


def check_vertical_monotonicity(surface_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible wrapper now backed by price monotonicity where prices exist."""
    report = build_price_based_surface_arbitrage_report(surface_snapshot)
    if report.get("price_check_available"):
        anomalies = []
        for check in report.get("checks", []):
            if check.get("check") in {"call_vertical_price_monotonicity", "put_vertical_price_monotonicity"}:
                anomalies.extend(check.get("anomalies", []))
        return {"ok": True, "anomaly_count": len(anomalies), "anomalies": anomalies, "caveat": "price_based_vertical_monotonicity", "research_only": True}
    anomalies: list[dict[str, Any]] = []
    for (expiry, option_type), rows in _group(surface_snapshot.get("points", []), "expiry", "option_type").items():
        sorted_rows = sorted(rows, key=lambda x: float(x.get("strike", 0)))
        prev = None
        for row in sorted_rows:
            iv = row.get("mid_iv")
            if prev is not None and iv is not None and abs(float(iv) - float(prev.get("mid_iv", iv))) > 1.5:
                anomalies.append({"check": "vertical_iv_jump_caveated_legacy", "expiry": expiry, "option_type": option_type, "strike": row.get("strike"), "research_only": True})
            if iv is not None:
                prev = row
    return {"ok": True, "anomaly_count": len(anomalies), "anomalies": anomalies, "caveat": "price_check_unavailable; legacy IV jump diagnostic only", "research_only": True}


def check_butterfly_convexity(surface_snapshot: dict[str, Any]) -> dict[str, Any]:
    price_check = check_option_price_convexity_by_strike(surface_snapshot)
    if price_check.get("caveat") != "price_check_unavailable":
        return price_check
    anomalies: list[dict[str, Any]] = []
    for (expiry, option_type), rows in _group(surface_snapshot.get("points", []), "expiry", "option_type").items():
        sorted_rows = sorted([r for r in rows if r.get("mid_iv") is not None], key=lambda x: float(x.get("strike", 0)))
        for a, b, c in zip(sorted_rows, sorted_rows[1:], sorted_rows[2:]):
            midpoint = (float(a["mid_iv"]) + float(c["mid_iv"])) / 2.0
            if float(b["mid_iv"]) > midpoint + 0.75:
                anomalies.append({"check": "butterfly_convexity_iv_spike_caveated_legacy", "expiry": expiry, "option_type": option_type, "strike": b.get("strike"), "research_only": True})
    return {"ok": True, "anomaly_count": len(anomalies), "anomalies": anomalies, "caveat": "price_check_unavailable; legacy IV spike diagnostic only", "research_only": True}


def check_calendar_monotonicity(surface_snapshot: dict[str, Any]) -> dict[str, Any]:
    price_check = check_calendar_price_monotonicity(surface_snapshot)
    if price_check.get("caveat") != "price_check_unavailable":
        return price_check
    anomalies: list[dict[str, Any]] = []
    by_strike = _group(surface_snapshot.get("points", []), "strike", "option_type")
    for (strike, option_type), rows in by_strike.items():
        dated = sorted([r for r in rows if r.get("days_to_expiry") is not None and r.get("mid_iv") is not None], key=lambda x: float(x["days_to_expiry"]))
        for prev, cur in zip(dated, dated[1:]):
            if float(cur["mid_iv"]) < 0 or float(prev["mid_iv"]) < 0:
                anomalies.append({"check": "negative_iv_caveated_legacy", "strike": strike, "option_type": option_type, "research_only": True})
    return {"ok": True, "anomaly_count": len(anomalies), "anomalies": anomalies, "caveat": "price_check_unavailable; legacy IV diagnostic only", "research_only": True}


def check_call_put_parity_diagnostics(surface_snapshot: dict[str, Any]) -> dict[str, Any]:
    return check_call_put_parity_residuals(surface_snapshot)
