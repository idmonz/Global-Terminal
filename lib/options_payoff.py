from __future__ import annotations

from math import inf
from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE


def single_option_payoff(option_type: str, underlying_price_at_expiry: float, strike: float, premium: float = 0.0, quantity: float = 1.0, contract_multiplier: float = 100.0, position: str = "long") -> float:
    side = str(option_type or "call").lower()
    if side not in {"call", "put"}:
        raise ValueError("option_type must be call or put")
    pos = str(position or "long").lower()
    if pos not in {"long", "short"}:
        raise ValueError("position must be long or short")
    s, k, p, q, m = map(float, [underlying_price_at_expiry, strike, premium, quantity, contract_multiplier])
    intrinsic = max(0.0, s - k) if side == "call" else max(0.0, k - s)
    pnl_per_unit = intrinsic - p
    if pos == "short":
        pnl_per_unit = -pnl_per_unit
    return pnl_per_unit * q * m


def payoff_table(legs: list[dict[str, Any]], price_grid: list[float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for price in price_grid:
        total = 0.0
        leg_values = []
        for leg in legs:
            value = single_option_payoff(
                leg.get("option_type", "call"), price, leg["strike"], leg.get("premium", 0.0), leg.get("quantity", 1.0), leg.get("contract_multiplier", 100.0), leg.get("position", "long")
            )
            total += value
            leg_values.append(value)
        rows.append({"underlying_price_at_expiry": float(price), "total_pnl": float(total), "leg_pnls": leg_values, "research_only": True})
    return rows


def _net_debit(legs: list[dict[str, Any]]) -> float:
    total = 0.0
    for leg in legs:
        sign = 1.0 if str(leg.get("position", "long")).lower() == "long" else -1.0
        total += sign * float(leg.get("premium", 0.0)) * float(leg.get("quantity", 1.0)) * float(leg.get("contract_multiplier", 100.0))
    return total


def breakeven_points(legs: list[dict[str, Any]], price_grid: list[float]) -> list[float]:
    rows = payoff_table(legs, sorted(float(v) for v in price_grid))
    points: list[float] = []
    for left, right in zip(rows, rows[1:]):
        y1, y2 = left["total_pnl"], right["total_pnl"]
        x1, x2 = left["underlying_price_at_expiry"], right["underlying_price_at_expiry"]
        if y1 == 0:
            points.append(x1)
        if y1 * y2 < 0:
            points.append(x1 + (0.0 - y1) * (x2 - x1) / (y2 - y1))
    if rows and rows[-1]["total_pnl"] == 0:
        points.append(rows[-1]["underlying_price_at_expiry"])
    deduped: list[float] = []
    for point in points:
        if not any(abs(point - existing) < 1e-8 for existing in deduped):
            deduped.append(float(point))
    return deduped


def payoff_summary(legs: list[dict[str, Any]], price_grid: list[float]) -> dict[str, Any]:
    rows = payoff_table(legs, price_grid)
    pnls = [r["total_pnl"] for r in rows]
    finite_min = min(pnls) if pnls else None
    finite_max = max(pnls) if pnls else None
    return {
        "ok": True,
        "legs": legs,
        "table": rows,
        "breakeven_points": breakeven_points(legs, price_grid),
        "net_debit_positive_or_credit_negative": _net_debit(legs),
        "max_loss_label": finite_min,
        "max_gain_label": finite_max,
        "grid_limited": True,
        "notice": RESEARCH_ONLY_OPTIONS_NOTICE,
        "research_only": True,
    }


def covered_call_payoff(underlying_cost: float, call_strike: float, call_premium: float, price_grid: list[float], shares: float = 100.0) -> dict[str, Any]:
    rows = []
    for price in price_grid:
        stock_pnl = (float(price) - float(underlying_cost)) * float(shares)
        call_pnl = single_option_payoff("call", price, call_strike, call_premium, 1.0, shares, "short")
        rows.append({"underlying_price_at_expiry": float(price), "stock_pnl": stock_pnl, "option_pnl": call_pnl, "total_pnl": stock_pnl + call_pnl})
    return {"strategy_template": "covered_call", "table": rows, "breakeven_points": [float(underlying_cost) - float(call_premium)], "max_gain_label": (float(call_strike) - float(underlying_cost) + float(call_premium)) * float(shares), "max_loss_label": "downside until underlying approaches zero, partially offset by premium", "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}


def protective_put_payoff(underlying_cost: float, put_strike: float, put_premium: float, price_grid: list[float], shares: float = 100.0) -> dict[str, Any]:
    rows = []
    for price in price_grid:
        stock_pnl = (float(price) - float(underlying_cost)) * float(shares)
        put_pnl = single_option_payoff("put", price, put_strike, put_premium, 1.0, shares, "long")
        rows.append({"underlying_price_at_expiry": float(price), "stock_pnl": stock_pnl, "option_pnl": put_pnl, "total_pnl": stock_pnl + put_pnl})
    return {"strategy_template": "protective_put", "table": rows, "breakeven_points": [float(underlying_cost) + float(put_premium)], "max_loss_label": (float(put_strike) - float(underlying_cost) - float(put_premium)) * float(shares), "max_gain_label": "grid-limited; upside depends on underlying path", "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}


def vertical_spread_payoff(option_type: str, lower_strike: float, upper_strike: float, lower_premium: float, upper_premium: float, price_grid: list[float], *, contract_multiplier: float = 100.0, lower_position: str = "long") -> dict[str, Any]:
    upper_position = "short" if lower_position == "long" else "long"
    legs = [
        {"option_type": option_type, "strike": lower_strike, "premium": lower_premium, "position": lower_position, "contract_multiplier": contract_multiplier},
        {"option_type": option_type, "strike": upper_strike, "premium": upper_premium, "position": upper_position, "contract_multiplier": contract_multiplier},
    ]
    return {**payoff_summary(legs, price_grid), "strategy_template": "vertical_spread"}


def straddle_payoff(strike: float, call_premium: float, put_premium: float, price_grid: list[float], *, contract_multiplier: float = 100.0, position: str = "long") -> dict[str, Any]:
    legs = [
        {"option_type": "call", "strike": strike, "premium": call_premium, "position": position, "contract_multiplier": contract_multiplier},
        {"option_type": "put", "strike": strike, "premium": put_premium, "position": position, "contract_multiplier": contract_multiplier},
    ]
    return {**payoff_summary(legs, price_grid), "strategy_template": "straddle"}


def strangle_payoff(call_strike: float, put_strike: float, call_premium: float, put_premium: float, price_grid: list[float], *, contract_multiplier: float = 100.0, position: str = "long") -> dict[str, Any]:
    legs = [
        {"option_type": "call", "strike": call_strike, "premium": call_premium, "position": position, "contract_multiplier": contract_multiplier},
        {"option_type": "put", "strike": put_strike, "premium": put_premium, "position": position, "contract_multiplier": contract_multiplier},
    ]
    return {**payoff_summary(legs, price_grid), "strategy_template": "strangle"}
