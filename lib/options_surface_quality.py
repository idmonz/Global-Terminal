from __future__ import annotations

from typing import Any
from .options_surface_arbitrage import check_butterfly_convexity, check_calendar_monotonicity, check_call_put_parity_diagnostics, check_vertical_monotonicity
from .options_surface_price_checks import build_price_based_surface_arbitrage_report


def build_surface_anomaly_table(surface_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    price_report = build_price_based_surface_arbitrage_report(surface_snapshot)
    if price_report.get("price_check_available"):
        return list(price_report.get("anomalies", []))
    checks = [
        check_vertical_monotonicity(surface_snapshot),
        check_butterfly_convexity(surface_snapshot),
        check_calendar_monotonicity(surface_snapshot),
    ]
    rows: list[dict[str, Any]] = []
    for payload in checks:
        rows.extend(payload.get("anomalies", []))
    parity = check_call_put_parity_diagnostics(surface_snapshot)
    if parity.get("missing_pair_count", 0):
        rows.append({"check": "missing_call_put_pairs", "count": parity["missing_pair_count"], "research_only": True})
    return rows


def build_surface_quality_score(surface_snapshot: dict[str, Any]) -> dict[str, Any]:
    points = surface_snapshot.get("points", [])
    point_count = len(points)
    no_solution = sum(1 for p in points if p.get("mid_iv") is None)
    interpolated = sum(1 for p in points if p.get("interpolated"))
    stale = sum(1 for p in points if str(p.get("freshness", "")).lower() in {"stale", "historical", "unknown"})
    wide = sum(1 for p in points if p.get("spread_pct") is not None and float(p.get("spread_pct")) > 0.25)
    model_mix = sorted({str(p.get("pricing_model") or p.get("model") or "unknown") for p in points})
    price_report = build_price_based_surface_arbitrage_report(surface_snapshot)
    anomalies = build_surface_anomaly_table(surface_snapshot)
    penalty = no_solution * 5 + interpolated * 2 + stale + wide * 3 + len(anomalies) * 4 + max(0, len(model_mix) - 1) * 3
    score = max(0.0, min(100.0, 100.0 - penalty - (20 if point_count < 6 else 0)))
    caveats = ["supplied_surface_only", "not_a_calibrated_forecast"]
    if point_count < 6:
        caveats.append("sparse_surface_caveat")
    if wide:
        caveats.append("wide_spread_contamination_caveat")
    if no_solution:
        caveats.append("no_solution_iv_points_present")
    if interpolated:
        caveats.append("interpolated_points_labeled")
    if stale:
        caveats.append("stale_or_unknown_source_share_present")
    if len(model_mix) > 1:
        caveats.append("model_mix_caveat")
    if not price_report.get("price_check_available"):
        caveats.extend(price_report.get("caveats", []))
    return {"ok": True, "score": score, "point_count": point_count, "no_solution_iv_count": no_solution, "interpolated_point_share": 0 if point_count == 0 else interpolated / point_count, "stale_or_historical_share": 0 if point_count == 0 else stale / point_count, "wide_spread_count": wide, "model_mix": model_mix, "anomaly_count": len(anomalies), "price_based_surface_arbitrage": price_report, "caveats": sorted(dict.fromkeys(caveats)), "research_only": True}
