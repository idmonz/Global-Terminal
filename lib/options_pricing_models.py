from __future__ import annotations

from math import erf, exp, log, pi, sqrt
from typing import Any

from .options_pricing_inputs import OptionPricingInput, RESEARCH_ONLY_OPTIONS_NOTICE
from .options_validation import validate_option_input

SQRT_2PI = sqrt(2.0 * pi)


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(float(x) / sqrt(2.0)))


def normal_pdf(x: float) -> float:
    return exp(-0.5 * float(x) * float(x)) / SQRT_2PI


def _sign(option_type: str) -> int:
    return 1 if option_type == "call" else -1


def black_scholes_d1_d2(underlying_price: float, strike: float, time_to_expiry_years: float, risk_free_rate: float, volatility: float, dividend_yield: float = 0.0) -> tuple[float, float]:
    sigma_sqrt_t = volatility * sqrt(time_to_expiry_years)
    d1 = (log(underlying_price / strike) + (risk_free_rate - dividend_yield + 0.5 * volatility * volatility) * time_to_expiry_years) / sigma_sqrt_t
    return d1, d1 - sigma_sqrt_t


def black_scholes_price(option_type: str, underlying_price: float, strike: float, time_to_expiry_years: float, risk_free_rate: float, volatility: float, dividend_yield: float = 0.0) -> float:
    inp = validate_option_input({"option_type": option_type, "underlying_price": underlying_price, "strike": strike, "time_to_expiry_years": time_to_expiry_years, "risk_free_rate": risk_free_rate, "dividend_yield": dividend_yield, "volatility": volatility, "model": "black_scholes"})
    d1, d2 = black_scholes_d1_d2(inp.underlying_price, inp.strike, inp.time_to_expiry_years, inp.risk_free_rate, inp.volatility, inp.dividend_yield)
    sgn = _sign(inp.option_type)
    return sgn * (inp.underlying_price * exp(-inp.dividend_yield * inp.time_to_expiry_years) * normal_cdf(sgn * d1) - inp.strike * exp(-inp.risk_free_rate * inp.time_to_expiry_years) * normal_cdf(sgn * d2))


def black_76_d1_d2(futures_price: float, strike: float, time_to_expiry_years: float, volatility: float) -> tuple[float, float]:
    sigma_sqrt_t = volatility * sqrt(time_to_expiry_years)
    d1 = (log(futures_price / strike) + 0.5 * volatility * volatility * time_to_expiry_years) / sigma_sqrt_t
    return d1, d1 - sigma_sqrt_t


def black_76_price(option_type: str, futures_price: float, strike: float, time_to_expiry_years: float, risk_free_rate: float, volatility: float) -> float:
    inp = validate_option_input({"option_type": option_type, "underlying_price": futures_price, "futures_price": futures_price, "strike": strike, "time_to_expiry_years": time_to_expiry_years, "risk_free_rate": risk_free_rate, "volatility": volatility, "model": "black_76"})
    d1, d2 = black_76_d1_d2(float(inp.futures_price), inp.strike, inp.time_to_expiry_years, inp.volatility)
    sgn = _sign(inp.option_type)
    return exp(-inp.risk_free_rate * inp.time_to_expiry_years) * sgn * (float(inp.futures_price) * normal_cdf(sgn * d1) - inp.strike * normal_cdf(sgn * d2))


def garman_kohlhagen_price(option_type: str, underlying_price: float, strike: float, time_to_expiry_years: float, domestic_rate: float, foreign_rate: float, volatility: float) -> float:
    inp = validate_option_input({"option_type": option_type, "underlying_price": underlying_price, "strike": strike, "time_to_expiry_years": time_to_expiry_years, "risk_free_rate": domestic_rate, "domestic_rate": domestic_rate, "foreign_rate": foreign_rate, "dividend_yield": foreign_rate, "volatility": volatility, "model": "garman_kohlhagen"})
    return black_scholes_price(inp.option_type, inp.underlying_price, inp.strike, inp.time_to_expiry_years, float(inp.domestic_rate), inp.volatility, float(inp.foreign_rate))


def price_option(input_data: OptionPricingInput | dict[str, Any]) -> dict[str, Any]:
    inp = validate_option_input(input_data)
    if inp.model == "black_76":
        price = black_76_price(inp.option_type, float(inp.futures_price), inp.strike, inp.time_to_expiry_years, inp.risk_free_rate, inp.volatility)
        model_label = "Black-76 futures option"
    elif inp.model == "garman_kohlhagen":
        price = garman_kohlhagen_price(inp.option_type, inp.underlying_price, inp.strike, inp.time_to_expiry_years, float(inp.domestic_rate), float(inp.foreign_rate), inp.volatility)
        model_label = "Garman-Kohlhagen FX option"
    else:
        price = black_scholes_price(inp.option_type, inp.underlying_price, inp.strike, inp.time_to_expiry_years, inp.risk_free_rate, inp.volatility, inp.dividend_yield)
        model_label = "Black-Scholes equity/index option"
    return {
        "ok": True,
        "model": inp.model,
        "model_label": model_label,
        "option_type": inp.option_type,
        "price": float(price),
        "contract_value": float(price * inp.contract_multiplier),
        "contract_multiplier": inp.contract_multiplier,
        "inputs": inp.to_dict(),
        "units": {"price": "premium per underlying unit", "contract_value": "premium * contract_multiplier"},
        "notice": RESEARCH_ONLY_OPTIONS_NOTICE,
        "research_only": True,
    }
