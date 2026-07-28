from __future__ import annotations

from math import exp
from typing import Any

from .options_chain_schema import GOAL12B_RESEARCH_ONLY_NOTICE
from .options_iv_solver import implied_volatility
from .options_time_to_expiry import derive_time_to_expiry_years
from .options_model_selector import build_row_pricing_input, infer_option_pricing_model_for_row


def compute_mid_price(bid: float | int | str | None, ask: float | int | str | None, mark: float | int | str | None = None, last: float | int | str | None = None) -> dict[str, Any]:
    try:
        b = float(bid) if bid not in (None, "") else None
        a = float(ask) if ask not in (None, "") else None
        if b is not None and a is not None:
            if b < 0 or a < 0 or b > a:
                return {"ok": False, "mid": None, "reason": "invalid_bid_ask", "research_only": True}
            return {"ok": True, "mid": (b + a) / 2.0, "method": "bid_ask_mid", "research_only": True}
        for value, method in [(mark, "mark"), (last, "last")]:
            if value not in (None, "") and float(value) > 0:
                return {"ok": True, "mid": float(value), "method": method, "research_only": True}
    except Exception:
        return {"ok": False, "mid": None, "reason": "invalid_price", "research_only": True}
    return {"ok": False, "mid": None, "reason": "missing_premium", "research_only": True}


def compute_bid_ask_spread(bid: float | int | str | None, ask: float | int | str | None) -> dict[str, Any]:
    try:
        b, a = float(bid), float(ask)
    except Exception:
        return {"ok": False, "spread": None, "spread_pct": None, "reason": "missing_or_invalid_bid_ask", "research_only": True}
    if b < 0 or a < 0 or b > a:
        return {"ok": False, "spread": None, "spread_pct": None, "reason": "invalid_or_crossed_bid_ask", "research_only": True}
    mid = (a + b) / 2.0
    return {"ok": True, "spread": a - b, "spread_pct": None if mid <= 0 else (a - b) / mid, "research_only": True}


def identify_no_arbitrage_violations(row: dict[str, Any], premium: float | None = None) -> list[str]:
    flags: list[str] = []
    try:
        s = float(row.get("underlying_price") or row.get("futures_price"))
        k = float(row.get("strike"))
        t = float(row.get("time_to_expiry_years"))
        r = float(row.get("risk_free_rate", row.get("domestic_rate", 0.0)) or 0.0)
        p = float(premium if premium is not None else row.get("mid", row.get("mark", row.get("last"))))
        side = str(row.get("option_type", "call")).lower()
    except Exception:
        return ["bounds_unavailable"]
    if side == "call":
        lower = max(0.0, s - k * exp(-r * t))
        upper = s
    else:
        lower = max(0.0, k * exp(-r * t) - s)
        upper = k * exp(-r * t)
    if p < lower - 1e-9:
        flags.append("premium_below_intrinsic_or_discount_bound")
    if p > upper + 1e-9:
        flags.append("premium_above_upper_bound")
    return flags


def _prepare_row(row: dict[str, Any], chain_snapshot: dict[str, Any] | None = None, risk_free_rate: float = 0.0) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    out = dict(row)
    out.setdefault("risk_free_rate", risk_free_rate)
    source_snapshot = (chain_snapshot or {}).get("source_snapshot", {})
    tte_payload = derive_time_to_expiry_years(out, snapshot_timestamp=source_snapshot.get("timestamp") or source_snapshot.get("asof"))
    if tte_payload.get("ok"):
        out["time_to_expiry_years"] = tte_payload["time_to_expiry_years"]
        out["days_to_expiry"] = tte_payload.get("days_to_expiry")
    model_payload = infer_option_pricing_model_for_row(out)
    out["model"] = model_payload.get("model", out.get("model", "manual_unknown"))
    out["model_selection_ok"] = bool(model_payload.get("ok"))
    return out, tte_payload, model_payload


def solve_row_implied_volatility(row: dict[str, Any], price_field: str = "mid") -> dict[str, Any]:
    premium = row.get(price_field)
    if premium in (None, ""):
        return {"ok": False, "converged": False, "implied_volatility": None, "error_reason": "missing_premium", "research_only": True}
    if row.get("time_to_expiry_years") in (None, ""):
        return {"ok": False, "converged": False, "implied_volatility": None, "error_reason": "missing_time_to_expiry", "research_only": True}
    try:
        base = build_row_pricing_input(row, premium=float(premium))
    except Exception as exc:
        return {"ok": False, "converged": False, "implied_volatility": None, "error_reason": f"input_build_failed: {exc}", "research_only": True}
    return implied_volatility(base, market_price=float(premium))


def classify_iv_status(result: dict[str, Any], spread_pct: float | None = None) -> str:
    if not result.get("ok"):
        return "no_solution"
    if spread_pct is not None and spread_pct > 0.25:
        return "wide_spread_caveat"
    return "solved"


def build_chain_iv_snapshot(chain_snapshot: dict[str, Any], *, default_tte_years: float | None = None, risk_free_rate: float = 0.0) -> dict[str, Any]:
    rows = []
    for raw in chain_snapshot.get("rows", []):
        row, tte_payload, model_payload = _prepare_row(raw, chain_snapshot, risk_free_rate)
        if default_tte_years is not None and not tte_payload.get("ok"):
            row["time_to_expiry_years"] = float(default_tte_years)
            row["days_to_expiry"] = float(default_tte_years) * 365.25
            tte_payload = {"ok": True, "status": "explicit_default", "caveat": "caller_supplied_default_tte", "time_to_expiry_years": default_tte_years, "days_to_expiry": row["days_to_expiry"], "research_only": True}
        mid = compute_mid_price(row.get("bid"), row.get("ask"), row.get("mark"), row.get("last"))
        spread = compute_bid_ask_spread(row.get("bid"), row.get("ask"))
        row["mid"] = mid.get("mid")
        if not tte_payload.get("ok"):
            bid_iv = ask_iv = mid_iv = {"ok": False, "implied_volatility": None, "error_reason": tte_payload.get("caveat", "missing_time_to_expiry")}
        elif not model_payload.get("ok"):
            reason = "pricing_skipped_missing_model"
            bid_iv = ask_iv = mid_iv = {"ok": False, "implied_volatility": None, "error_reason": reason}
        else:
            bid_iv = solve_row_implied_volatility({**row, "mid": row.get("bid")}, "mid") if row.get("bid") not in (None, "") else {"ok": False, "implied_volatility": None, "error_reason": "missing_bid"}
            ask_iv = solve_row_implied_volatility({**row, "mid": row.get("ask")}, "mid") if row.get("ask") not in (None, "") else {"ok": False, "implied_volatility": None, "error_reason": "missing_ask"}
            mid_iv = solve_row_implied_volatility(row, "mid") if mid.get("ok") else {"ok": False, "implied_volatility": None, "error_reason": mid.get("reason", "missing_mid")}
        violations = identify_no_arbitrage_violations(row, mid.get("mid")) if mid.get("mid") is not None and row.get("time_to_expiry_years") not in (None, "") else ["missing_price_or_tte_status"]
        rows.append({
            **row,
            "model_selection": model_payload,
            "pricing_model": row.get("model"),
            "tte_status": tte_payload.get("status"),
            "tte_caveat": tte_payload.get("caveat"),
            "bid_iv": bid_iv.get("implied_volatility"),
            "ask_iv": ask_iv.get("implied_volatility"),
            "mid_iv": mid_iv.get("implied_volatility"),
            "supplied_iv": row.get("implied_volatility"),
            "iv_status": "pricing_skipped_missing_model" if mid_iv.get("error_reason") == "pricing_skipped_missing_model" else classify_iv_status(mid_iv, spread.get("spread_pct")),
            "spread_pct": spread.get("spread_pct"),
            "intrinsic_bound_status": "ok" if not violations else ",".join(violations),
            "no_solution_reason": "" if mid_iv.get("ok") else mid_iv.get("error_reason", "no_solution"),
            "stale_or_wide_spread_caveat": bool(spread.get("spread_pct") is not None and spread.get("spread_pct") > 0.25),
            "research_only": True,
        })
    return {
        "ok": True,
        "snapshot_id": chain_snapshot.get("snapshot_id", "option_chain_snapshot_supplied") + "_iv",
        "rows": rows,
        "solved_count": sum(1 for r in rows if r.get("mid_iv") is not None),
        "no_solution_count": sum(1 for r in rows if r.get("mid_iv") is None),
        "model_mix": sorted({str(r.get("pricing_model")) for r in rows if r.get("pricing_model")}),
        "source_snapshot": chain_snapshot.get("source_snapshot", {"source": "user_supplied_csv", "freshness": "unknown"}),
        "notice": GOAL12B_RESEARCH_ONLY_NOTICE,
        "research_only": True,
    }
