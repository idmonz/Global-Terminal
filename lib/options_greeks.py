from __future__ import annotations

from math import exp, sqrt
from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE
from .options_pricing_models import black_76_d1_d2, black_76_price, black_scholes_d1_d2, garman_kohlhagen_price, normal_cdf, normal_pdf, price_option
from .options_validation import validate_option_input


def black_scholes_greeks(option_type: str, underlying_price: float, strike: float, time_to_expiry_years: float, risk_free_rate: float, volatility: float, dividend_yield: float = 0.0) -> dict[str, float]:
    inp = validate_option_input({"option_type": option_type, "underlying_price": underlying_price, "strike": strike, "time_to_expiry_years": time_to_expiry_years, "risk_free_rate": risk_free_rate, "volatility": volatility, "dividend_yield": dividend_yield, "model": "black_scholes"})
    s, k, t, r, q, v = inp.underlying_price, inp.strike, inp.time_to_expiry_years, inp.risk_free_rate, inp.dividend_yield, inp.volatility
    d1, d2 = black_scholes_d1_d2(s, k, t, r, v, q)
    pdf = normal_pdf(d1)
    if inp.option_type == "call":
        delta = exp(-q * t) * normal_cdf(d1)
        theta = (-(s * exp(-q * t) * pdf * v) / (2 * sqrt(t)) - r * k * exp(-r * t) * normal_cdf(d2) + q * s * exp(-q * t) * normal_cdf(d1))
        rho = k * t * exp(-r * t) * normal_cdf(d2)
        carry_sensitivity = -t * s * exp(-q * t) * normal_cdf(d1)
    else:
        delta = exp(-q * t) * (normal_cdf(d1) - 1)
        theta = (-(s * exp(-q * t) * pdf * v) / (2 * sqrt(t)) + r * k * exp(-r * t) * normal_cdf(-d2) - q * s * exp(-q * t) * normal_cdf(-d1))
        rho = -k * t * exp(-r * t) * normal_cdf(-d2)
        carry_sensitivity = t * s * exp(-q * t) * normal_cdf(-d1)
    gamma = exp(-q * t) * pdf / (s * v * sqrt(t))
    vega = s * exp(-q * t) * pdf * sqrt(t)
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "theta_per_day": theta / 365.0, "rho": rho, "carry_or_dividend_sensitivity": carry_sensitivity}


def black_76_greeks(option_type: str, futures_price: float, strike: float, time_to_expiry_years: float, risk_free_rate: float, volatility: float) -> dict[str, float]:
    inp = validate_option_input({"option_type": option_type, "underlying_price": futures_price, "futures_price": futures_price, "strike": strike, "time_to_expiry_years": time_to_expiry_years, "risk_free_rate": risk_free_rate, "volatility": volatility, "model": "black_76"})
    f, k, t, r, v = float(inp.futures_price), inp.strike, inp.time_to_expiry_years, inp.risk_free_rate, inp.volatility
    d1, d2 = black_76_d1_d2(f, k, t, v)
    disc = exp(-r * t)
    pdf = normal_pdf(d1)
    if inp.option_type == "call":
        delta = disc * normal_cdf(d1)
    else:
        delta = -disc * normal_cdf(-d1)
    gamma = disc * pdf / (f * v * sqrt(t))
    vega = disc * f * pdf * sqrt(t)
    price = black_76_price(inp.option_type, f, k, t, r, v)
    theta = -f * disc * pdf * v / (2 * sqrt(t)) + r * price
    rho = -t * price
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "theta_per_day": theta / 365.0, "rho": rho, "carry_or_dividend_sensitivity": 0.0}


def garman_kohlhagen_greeks(option_type: str, underlying_price: float, strike: float, time_to_expiry_years: float, domestic_rate: float, foreign_rate: float, volatility: float) -> dict[str, float]:
    return black_scholes_greeks(option_type, underlying_price, strike, time_to_expiry_years, domestic_rate, volatility, foreign_rate)


def calculate_greeks(input_data: dict[str, Any]) -> dict[str, Any]:
    inp = validate_option_input(input_data)
    if inp.model == "black_76":
        greeks = black_76_greeks(inp.option_type, float(inp.futures_price), inp.strike, inp.time_to_expiry_years, inp.risk_free_rate, inp.volatility)
    elif inp.model == "garman_kohlhagen":
        greeks = garman_kohlhagen_greeks(inp.option_type, inp.underlying_price, inp.strike, inp.time_to_expiry_years, float(inp.domestic_rate), float(inp.foreign_rate), inp.volatility)
    else:
        greeks = black_scholes_greeks(inp.option_type, inp.underlying_price, inp.strike, inp.time_to_expiry_years, inp.risk_free_rate, inp.volatility, inp.dividend_yield)
    priced = price_option(inp)
    return {"ok": True, "model": inp.model, "price": priced["price"], "greeks": {k: float(v) for k, v in greeks.items()}, "units": {"vega": "price change per 1.00 volatility point", "theta": "price change per year", "theta_per_day": "price change per calendar day", "rho": "price change per 1.00 rate point"}, "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}



def scale_greeks_by_contract(greeks: dict[str, Any], *, contract_multiplier: float = 100.0, quantity: float = 1.0, underlying_price: float | None = None) -> dict[str, Any]:
    multiplier = float(contract_multiplier)
    qty = float(quantity)
    delta = float(greeks.get("delta", 0.0))
    gamma = float(greeks.get("gamma", 0.0))
    vega = float(greeks.get("vega", 0.0))
    theta = float(greeks.get("theta", 0.0))
    theta_per_day = float(greeks.get("theta_per_day", theta / 365.0))
    rho = float(greeks.get("rho", 0.0))
    scaled = {
        "contract_delta": delta * multiplier * qty,
        "contract_gamma": gamma * multiplier * qty,
        "contract_vega_1pct": vega * 0.01 * multiplier * qty,
        "contract_theta_1day": theta_per_day * multiplier * qty,
        "contract_rho_1bp": rho * 0.0001 * multiplier * qty,
        "vega_1pct": vega * 0.01,
        "rho_1bp": rho * 0.0001,
        "theta_1day": theta_per_day,
        "quantity": qty,
        "contract_multiplier": multiplier,
        "notional_delta_approx": None if underlying_price is None else delta * multiplier * qty * float(underlying_price),
        "research_only": True,
    }
    return scaled


def build_greek_units_table(contract_multiplier: float = 100.0) -> list[dict[str, Any]]:
    return [
        {"field": "delta", "unit": "premium change per 1 underlying unit", "contract_scaled": "delta * multiplier * quantity"},
        {"field": "gamma", "unit": "delta change per 1 underlying unit", "contract_scaled": "gamma * multiplier * quantity"},
        {"field": "vega_1pct", "unit": "premium change per 1 percentage-point volatility move", "contract_scaled": "vega * 0.01 * multiplier * quantity"},
        {"field": "theta_1day", "unit": "premium change per calendar day", "contract_scaled": "theta_per_day * multiplier * quantity"},
        {"field": "rho_1bp", "unit": "premium change per 1 basis-point rate move", "contract_scaled": "rho * 0.0001 * multiplier * quantity"},
        {"field": "contract_multiplier", "unit": str(float(contract_multiplier)), "contract_scaled": "user supplied or default multiplier"},
    ]
