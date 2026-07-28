from __future__ import annotations

from typing import Any

from .options_greeks import calculate_greeks
from .options_payoff import payoff_table
from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE
from .options_pricing_models import price_option
from .options_validation import validate_option_input, validate_scenario_grid


def build_price_shock_grid(spot: float, shocks: list[float] | None = None) -> list[float]:
    shocks = shocks if shocks is not None else [-0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2]
    return [float(spot) * (1.0 + float(shock)) for shock in shocks]


def build_volatility_shock_grid(volatility: float, shocks: list[float] | None = None) -> list[float]:
    shocks = shocks if shocks is not None else [-0.10, -0.05, 0.0, 0.05, 0.10]
    return [max(1e-6, float(volatility) + float(shock)) for shock in shocks]


def build_time_decay_grid(time_to_expiry_years: float, points: int = 5) -> list[float]:
    t = float(time_to_expiry_years)
    points = max(2, int(points))
    return [max(1e-6, t * (points - i) / points) for i in range(points)]


def option_scenario_grid(input_data: dict[str, Any], *, price_grid: list[float] | None = None, volatility_grid: list[float] | None = None, time_grid: list[float] | None = None, rate_grid: list[float] | None = None) -> dict[str, Any]:
    inp = validate_option_input(input_data)
    prices = validate_scenario_grid(price_grid or build_price_shock_grid(inp.underlying_price), "underlying_price")
    vols = validate_scenario_grid(volatility_grid or build_volatility_shock_grid(inp.volatility), "volatility")
    times = validate_scenario_grid(time_grid or build_time_decay_grid(inp.time_to_expiry_years), "time_to_expiry_years")
    rates = [float(v) for v in (rate_grid if rate_grid is not None else [inp.risk_free_rate])]
    rows = []
    for s in prices:
        for vol in vols:
            for t in times:
                for rate in rates:
                    data = inp.to_dict()
                    data.update({"underlying_price": s, "volatility": vol, "time_to_expiry_years": t, "risk_free_rate": rate})
                    if data.get("model") == "black_76":
                        data["futures_price"] = s
                    if data.get("model") == "garman_kohlhagen" and data.get("domestic_rate") is not None:
                        data["domestic_rate"] = rate
                    priced = price_option(data)
                    pnl = None if inp.premium is None else (priced["price"] - float(inp.premium)) * inp.contract_multiplier
                    greeks = calculate_greeks(data)["greeks"]
                    rows.append({"underlying_price": s, "volatility": vol, "time_to_expiry_years": t, "risk_free_rate": rate, "price": priced["price"], "pnl_from_supplied_premium": pnl, "delta": greeks["delta"], "gamma": greeks["gamma"], "vega": greeks["vega"], "theta_per_day": greeks["theta_per_day"], "research_only": True})
    return {"ok": True, "scenario_count": len(rows), "rows": rows, "base_inputs": inp.to_dict(), "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}


def build_payoff_scenario(legs: list[dict[str, Any]], price_grid: list[float]) -> dict[str, Any]:
    return {"ok": True, "rows": payoff_table(legs, price_grid), "legs": legs, "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
