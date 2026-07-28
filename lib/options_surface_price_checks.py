from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def _points(surface_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return list(surface_snapshot.get("points", []) or [])


def _price(row: dict[str, Any]) -> float | None:
    for key in ("mid_price", "mid", "mark", "last"):
        value = row.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except Exception:
                return None
    bid, ask = row.get("bid"), row.get("ask")
    if bid not in (None, "") and ask not in (None, ""):
        try:
            b, a = float(bid), float(ask)
            if b >= 0 and a >= b:
                return (b + a) / 2.0
        except Exception:
            return None
    return None


def _group(points: list[dict[str, Any]], *keys: str) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for p in points:
        out[tuple(p.get(k) for k in keys)].append(p)
    return out


def _price_rows(surface_snapshot: dict[str, Any], *, option_type: str | None = None) -> list[dict[str, Any]]:
    rows = []
    for p in _points(surface_snapshot):
        if option_type and str(p.get("option_type", "")).lower() != option_type:
            continue
        px = _price(p)
        if px is None:
            continue
        rows.append({**p, "_price": px})
    return rows


def _unavailable(name: str) -> dict[str, Any]:
    return {"ok": True, "check": name, "anomaly_count": 0, "anomalies": [], "caveat": "price_check_unavailable", "research_only": True}


def check_call_vertical_price_monotonicity(surface_snapshot: dict[str, Any], *, tolerance: float = 1e-8) -> dict[str, Any]:
    rows = _price_rows(surface_snapshot, option_type="call")
    if len(rows) < 2:
        return _unavailable("call_vertical_price_monotonicity")
    anomalies = []
    for (expiry,), group in _group(rows, "expiry").items():
        sorted_rows = sorted(group, key=lambda x: float(x.get("strike", 0)))
        for prev, cur in zip(sorted_rows, sorted_rows[1:]):
            if cur["_price"] > prev["_price"] + tolerance:
                anomalies.append({"check": "call_vertical_price_monotonicity", "expiry": expiry, "lower_strike": prev.get("strike"), "higher_strike": cur.get("strike"), "lower_price": prev["_price"], "higher_price": cur["_price"], "research_only": True})
    return {"ok": True, "check": "call_vertical_price_monotonicity", "anomaly_count": len(anomalies), "anomalies": anomalies, "caveat": "uses_supplied_mid_mark_or_bid_ask_mid_prices", "research_only": True}


def check_put_vertical_price_monotonicity(surface_snapshot: dict[str, Any], *, tolerance: float = 1e-8) -> dict[str, Any]:
    rows = _price_rows(surface_snapshot, option_type="put")
    if len(rows) < 2:
        return _unavailable("put_vertical_price_monotonicity")
    anomalies = []
    for (expiry,), group in _group(rows, "expiry").items():
        sorted_rows = sorted(group, key=lambda x: float(x.get("strike", 0)))
        for prev, cur in zip(sorted_rows, sorted_rows[1:]):
            if cur["_price"] + tolerance < prev["_price"]:
                anomalies.append({"check": "put_vertical_price_monotonicity", "expiry": expiry, "lower_strike": prev.get("strike"), "higher_strike": cur.get("strike"), "lower_price": prev["_price"], "higher_price": cur["_price"], "research_only": True})
    return {"ok": True, "check": "put_vertical_price_monotonicity", "anomaly_count": len(anomalies), "anomalies": anomalies, "caveat": "uses_supplied_mid_mark_or_bid_ask_mid_prices", "research_only": True}


def check_option_price_convexity_by_strike(surface_snapshot: dict[str, Any], *, tolerance: float = 1e-8) -> dict[str, Any]:
    rows = _price_rows(surface_snapshot)
    if len(rows) < 3:
        return _unavailable("option_price_convexity_by_strike")
    anomalies = []
    for (expiry, option_type), group in _group(rows, "expiry", "option_type").items():
        sorted_rows = sorted(group, key=lambda x: float(x.get("strike", 0)))
        for a, b, c in zip(sorted_rows, sorted_rows[1:], sorted_rows[2:]):
            k1, k2, k3 = float(a.get("strike")), float(b.get("strike")), float(c.get("strike"))
            if k3 == k1:
                continue
            linear = a["_price"] + (c["_price"] - a["_price"]) * ((k2 - k1) / (k3 - k1))
            # Convex option-price curves lie below the chord between neighboring strikes.
            # A middle price above the linear interpolation bound is the diagnostic anomaly.
            if b["_price"] > linear + tolerance:
                anomalies.append({"check": "option_price_convexity_by_strike", "expiry": expiry, "option_type": option_type, "strike": b.get("strike"), "price": b["_price"], "linear_bound": linear, "research_only": True})
    return {"ok": True, "check": "option_price_convexity_by_strike", "anomaly_count": len(anomalies), "anomalies": anomalies, "caveat": "convexity uses supplied price points only; sparse surfaces are caveated", "research_only": True}


def check_calendar_price_monotonicity(surface_snapshot: dict[str, Any], *, tolerance: float = 1e-8) -> dict[str, Any]:
    rows = [r for r in _price_rows(surface_snapshot) if r.get("days_to_expiry") is not None or r.get("time_to_expiry_years") is not None]
    if len(rows) < 2:
        return _unavailable("calendar_price_monotonicity")
    anomalies = []
    for (strike, option_type), group in _group(rows, "strike", "option_type").items():
        def t(row: dict[str, Any]) -> float:
            if row.get("days_to_expiry") is not None:
                return float(row.get("days_to_expiry"))
            return float(row.get("time_to_expiry_years")) * 365.25
        sorted_rows = sorted(group, key=t)
        for near, far in zip(sorted_rows, sorted_rows[1:]):
            if far["_price"] + tolerance < near["_price"]:
                anomalies.append({"check": "calendar_price_monotonicity", "strike": strike, "option_type": option_type, "near_expiry": near.get("expiry"), "far_expiry": far.get("expiry"), "near_price": near["_price"], "far_price": far["_price"], "caveat": "calendar check ignores carry/dividend effects when not fully supplied", "research_only": True})
    return {"ok": True, "check": "calendar_price_monotonicity", "anomaly_count": len(anomalies), "anomalies": anomalies, "caveat": "calendar check is caveated when rates/carry/dividends are missing", "research_only": True}


def _parity_expected(row: dict[str, Any], option_type: str, call: dict[str, Any], put: dict[str, Any]) -> tuple[float | None, str]:
    try:
        k = float(row.get("strike"))
        t = float(row.get("time_to_expiry_years") if row.get("time_to_expiry_years") not in (None, "") else float(row.get("days_to_expiry", 0.0)) / 365.25)
        model = str(row.get("pricing_model") or row.get("model") or "").lower()
        r = float(row.get("risk_free_rate", row.get("domestic_rate", 0.0)) or 0.0)
        if model == "black_76" or row.get("futures_price") not in (None, ""):
            f = float(row.get("futures_price") or row.get("underlying_price"))
            return math.exp(-r * t) * (f - k), "futures"
        if model == "garman_kohlhagen" or row.get("foreign_rate") not in (None, ""):
            s = float(row.get("underlying_price"))
            rd = float(row.get("domestic_rate", row.get("risk_free_rate", 0.0)) or 0.0)
            rf = float(row.get("foreign_rate", row.get("dividend_yield", 0.0)) or 0.0)
            return s * math.exp(-rf * t) - k * math.exp(-rd * t), "fx"
        s = float(row.get("underlying_price"))
        q = float(row.get("dividend_yield", 0.0) or 0.0)
        return s * math.exp(-q * t) - k * math.exp(-r * t), "equity_index"
    except Exception:
        return None, "parity_inputs_missing"


def check_call_put_parity_residuals(surface_snapshot: dict[str, Any], *, tolerance: float = 0.25) -> dict[str, Any]:
    points = _points(surface_snapshot)
    raw_calls = {(p.get("expiry"), p.get("strike")): p for p in points if str(p.get("option_type", "")).lower() == "call"}
    raw_puts = {(p.get("expiry"), p.get("strike")): p for p in points if str(p.get("option_type", "")).lower() == "put"}
    raw_missing_pairs = [key for key in set(raw_calls) ^ set(raw_puts)]
    calls = {key: p for key, p in raw_calls.items() if _price(p) is not None}
    puts = {key: p for key, p in raw_puts.items() if _price(p) is not None}
    missing_pairs = [key for key in set(calls) ^ set(puts)] or raw_missing_pairs
    residuals = []
    anomalies = []
    for key in sorted(set(calls) & set(puts), key=lambda x: (str(x[0]), float(x[1]))):
        call, put = calls[key], puts[key]
        expected, model_family = _parity_expected(call, "call", call, put)
        if expected is None:
            residuals.append({"expiry": key[0], "strike": key[1], "status": model_family, "research_only": True})
            continue
        observed = float(_price(call)) - float(_price(put))
        residual = observed - expected
        row = {"expiry": key[0], "strike": key[1], "observed_call_minus_put": observed, "expected_call_minus_put": expected, "parity_residual": residual, "model_family": model_family, "within_tolerance": abs(residual) <= tolerance, "research_only": True}
        residuals.append(row)
        if abs(residual) > tolerance:
            anomalies.append({**row, "check": "call_put_parity_residual"})
    return {"ok": True, "paired_count": len(set(calls) & set(puts)), "missing_pair_count": len(missing_pairs), "missing_pairs": missing_pairs[:50], "residuals": residuals, "anomaly_count": len(anomalies), "anomalies": anomalies, "caveat": "put-call parity residuals use supplied prices/rates and are not a calibrated arbitrage-free proof", "research_only": True}


def build_price_based_surface_arbitrage_report(surface_snapshot: dict[str, Any]) -> dict[str, Any]:
    price_available = any(_price(p) is not None for p in _points(surface_snapshot))
    if not price_available:
        return {"ok": True, "price_check_available": False, "checks": [], "anomaly_count": 0, "anomalies": [], "caveats": ["price_check_unavailable", "iv_only_surface_not_price_noarb_checked"], "research_only": True}
    checks = [
        check_call_vertical_price_monotonicity(surface_snapshot),
        check_put_vertical_price_monotonicity(surface_snapshot),
        check_option_price_convexity_by_strike(surface_snapshot),
        check_calendar_price_monotonicity(surface_snapshot),
        check_call_put_parity_residuals(surface_snapshot),
    ]
    anomalies = [a for check in checks for a in check.get("anomalies", [])]
    caveats = sorted({str(check.get("caveat")) for check in checks if check.get("caveat")})
    return {"ok": True, "price_check_available": True, "checks": checks, "anomaly_count": len(anomalies), "anomalies": anomalies, "caveats": caveats + ["research_only_price_based_surface_diagnostics"], "research_only": True}
