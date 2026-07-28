from __future__ import annotations

from typing import Any

from .options_book_risk import build_option_book_risk_snapshot
from .options_model_selector import build_row_pricing_input, infer_option_pricing_model_for_row
from .options_pricing_models import price_option
from .options_time_to_expiry import derive_time_to_expiry_years


def _signed_qty(position: dict[str, Any]) -> float:
    return (1.0 if str(position.get("position", "long")).lower() == "long" else -1.0) * float(position.get("quantity", 1.0))


def _derive_position_tte(position: dict[str, Any]) -> dict[str, Any]:
    return derive_time_to_expiry_years(position, snapshot_timestamp=position.get("snapshot_timestamp"))


def _static_mark_payload(position: dict[str, Any], *, status: str, caveat: str) -> dict[str, Any]:
    price = float(position.get("mark", position.get("premium", 0.0)) or 0.0)
    qty = _signed_qty(position)
    multiplier = float(position.get("contract_multiplier", 100.0) or 100.0)
    return {
        "ok": False,
        "scenario_price": price,
        "base_mark": price,
        "scenario_value": price * multiplier * qty,
        "base_value": price * multiplier * qty,
        "scenario_pnl": 0.0,
        "reason": caveat,
        "repricing_status": status,
        "caveat": caveat,
        "research_only": True,
    }


def _position_value(position: dict[str, Any], *, price_shock: float = 0.0, vol_shock: float = 0.0, time_decay_days: float = 0.0, rate_shock: float = 0.0) -> dict[str, Any]:
    base_price = float(position.get("underlying_price") or position.get("futures_price") or 0.0)
    shocked_underlying = max(1e-9, base_price * (1.0 + float(price_shock)))
    tte_payload = _derive_position_tte(position)
    tte_status = tte_payload.get("status")
    if not tte_payload.get("ok"):
        if tte_status == "expired":
            payload = _static_mark_payload(position, status="expired_option", caveat="expired_option")
        else:
            payload = _static_mark_payload(position, status="tte_missing_reprice_skipped", caveat="tte_missing_reprice_skipped")
        return {**payload, "time_to_expiry_years": None, "tte_status": tte_status, "tte_caveat": tte_payload.get("caveat")}
    tte = float(tte_payload["time_to_expiry_years"])
    shocked_tte = tte - float(time_decay_days) / 365.25
    if shocked_tte <= 0:
        payload = _static_mark_payload(position, status="expired_option", caveat="expired_after_time_decay")
        return {**payload, "time_to_expiry_years": tte, "tte_status": tte_status, "tte_caveat": "expired_after_time_decay"}
    implied_vol = max(1e-6, float(position.get("implied_volatility", position.get("volatility", 0.2)) or 0.2) + float(vol_shock))
    row = {
        **position,
        "underlying_price": shocked_underlying,
        "time_to_expiry_years": shocked_tte,
        "implied_volatility": implied_vol,
        "volatility": implied_vol,
        "risk_free_rate": float(position.get("risk_free_rate", position.get("domestic_rate", 0.0)) or 0.0) + float(rate_shock),
    }
    if infer_option_pricing_model_for_row(row).get("model") == "black_76":
        row["futures_price"] = shocked_underlying
    try:
        inp = build_row_pricing_input(row, volatility=implied_vol)
        price = float(price_option(inp)["price"])
        ok = True
        reason = "repriced"
        repricing_status = "repriced"
        caveat = "full_reprice_where_possible"
    except Exception as exc:
        fallback = _static_mark_payload(position, status="repricing_failed_mark_only", caveat=f"pricing_unavailable: {exc}")
        return {**fallback, "time_to_expiry_years": tte, "tte_status": tte_status, "tte_caveat": tte_payload.get("caveat")}
    qty = _signed_qty(position)
    multiplier = float(position.get("contract_multiplier", 100.0) or 100.0)
    base_mark = float(position.get("mark", position.get("premium", 0.0)) or 0.0)
    return {
        "ok": ok,
        "scenario_price": price,
        "base_mark": base_mark,
        "scenario_value": price * multiplier * qty,
        "base_value": base_mark * multiplier * qty,
        "scenario_pnl": (price - base_mark) * multiplier * qty,
        "reason": reason,
        "repricing_status": repricing_status,
        "caveat": caveat,
        "time_to_expiry_years": tte,
        "tte_status": tte_status,
        "tte_caveat": tte_payload.get("caveat"),
        "research_only": True,
    }


def build_option_book_price_shock_grid(positions: list[dict[str, Any]], shocks: list[float] | None = None) -> list[dict[str, Any]]:
    shocks = shocks or [-0.10, -0.05, 0.0, 0.05, 0.10]
    return [{"price_shock": s, **aggregate_option_book_scenario_pnl(positions, price_shock=s)} for s in shocks]


def build_option_book_vol_shock_grid(positions: list[dict[str, Any]], shocks: list[float] | None = None) -> list[dict[str, Any]]:
    shocks = shocks or [-0.10, -0.05, 0.0, 0.05, 0.10]
    return [{"vol_shock": s, **aggregate_option_book_scenario_pnl(positions, vol_shock=s)} for s in shocks]


def build_option_book_time_decay_grid(positions: list[dict[str, Any]], days: list[float] | None = None) -> list[dict[str, Any]]:
    days = days or [0, 1, 7, 14, 30]
    return [{"time_decay_days": d, **aggregate_option_book_scenario_pnl(positions, time_decay_days=d)} for d in days]


def aggregate_option_book_scenario_pnl(positions: list[dict[str, Any]], *, price_shock: float = 0.0, vol_shock: float = 0.0, time_decay_days: float = 0.0, rate_shock: float = 0.0) -> dict[str, Any]:
    rows = [_position_value(p, price_shock=price_shock, vol_shock=vol_shock, time_decay_days=time_decay_days, rate_shock=rate_shock) for p in positions]
    return {
        "ok": True,
        "position_count": len(rows),
        "scenario_pnl": sum(float(r.get("scenario_pnl", 0.0)) for r in rows),
        "scenario_value": sum(float(r.get("scenario_value", 0.0)) for r in rows),
        "base_value": sum(float(r.get("base_value", 0.0)) for r in rows),
        "repriced_count": sum(1 for r in rows if r.get("repricing_status") == "repriced"),
        "reprice_skipped_count": sum(1 for r in rows if r.get("repricing_status") != "repriced"),
        "rows": rows,
        "caveat": "stress output uses supplied marks and local formula repricing only when reliable TTE/model fields are available",
        "research_only": True,
    }


def build_option_book_stress_snapshot(rows_or_positions: list[dict[str, Any]], *, price_shocks: list[float] | None = None, vol_shocks: list[float] | None = None, time_decay_days: list[float] | None = None) -> dict[str, Any]:
    risk = build_option_book_risk_snapshot(rows_or_positions)
    positions = risk.get("positions", [])
    return {
        "ok": risk.get("ok", True),
        "risk_snapshot": risk,
        "price_shock_grid": build_option_book_price_shock_grid(positions, price_shocks),
        "vol_shock_grid": build_option_book_vol_shock_grid(positions, vol_shocks),
        "time_decay_grid": build_option_book_time_decay_grid(positions, time_decay_days),
        "source_snapshot": risk.get("source_snapshot", {}),
        "caveats": ["supplied_positions_only", "stress_report_not_advice", "greeks_approximation_caveat", "full_reprice_requires_reliable_tte_and_model", "no_default_30_day_tte"],
        "research_only": True,
    }
