from __future__ import annotations

from typing import Any

from .options_pricing_inputs import OptionPricingInput, build_option_input, normalize_model, normalize_option_type


def _as_float(value: Any, field: str, *, allow_none: bool = False) -> float | None:
    if value is None and allow_none:
        return None
    try:
        return float(value)
    except Exception as exc:  # pragma: no cover - exact exception type is not important here
        raise ValueError(f"{field} must be numeric") from exc


def validate_option_input(input_data: OptionPricingInput | dict[str, Any]) -> OptionPricingInput:
    if isinstance(input_data, OptionPricingInput):
        data = input_data.to_dict()
    else:
        data = dict(input_data or {})
    data["option_type"] = normalize_option_type(data.get("option_type", "call"))
    data["model"] = normalize_model(data.get("model", "black_scholes"))

    required = ["underlying_price", "strike", "time_to_expiry_years", "risk_free_rate", "volatility"]
    missing = [field for field in required if field not in data or data[field] is None]
    if missing:
        raise ValueError(f"missing required option fields: {', '.join(missing)}")

    for field in [
        "underlying_price", "strike", "time_to_expiry_years", "risk_free_rate", "dividend_yield", "volatility",
        "contract_multiplier", "premium", "carry_rate", "futures_price", "foreign_rate", "domestic_rate",
    ]:
        if field in data:
            data[field] = _as_float(data.get(field), field, allow_none=field in {"premium", "carry_rate", "futures_price", "foreign_rate", "domestic_rate"})

    if data["underlying_price"] <= 0:
        raise ValueError("underlying_price must be positive")
    if data["strike"] <= 0:
        raise ValueError("strike must be positive")
    if data["time_to_expiry_years"] <= 0:
        raise ValueError("time_to_expiry_years must be positive")
    if data["volatility"] < 0:
        raise ValueError("volatility cannot be negative")
    if data["volatility"] == 0:
        raise ValueError("volatility must be positive for closed-form pricing")
    if data.get("contract_multiplier", 100.0) <= 0:
        raise ValueError("contract_multiplier must be positive")
    if data["model"] == "black_76":
        if data.get("futures_price") is None:
            data["futures_price"] = data["underlying_price"]
        if data["futures_price"] <= 0:
            raise ValueError("futures_price must be positive for black_76")
    if data["model"] == "garman_kohlhagen":
        if data.get("domestic_rate") is None:
            data["domestic_rate"] = data["risk_free_rate"]
        if data.get("foreign_rate") is None:
            data["foreign_rate"] = data.get("dividend_yield", 0.0)
    allowed_fields = {
        "option_type", "underlying_price", "strike", "time_to_expiry_years", "risk_free_rate", "volatility",
        "model", "dividend_yield", "carry_rate", "futures_price", "foreign_rate", "domestic_rate",
        "contract_multiplier", "premium",
    }
    return build_option_input(**{key: value for key, value in data.items() if key in allowed_fields})


def validate_scenario_grid(values: list[float], field: str) -> list[float]:
    if not values:
        raise ValueError(f"{field} scenario grid cannot be empty")
    out = [float(v) for v in values]
    if field in {"underlying_price", "volatility", "time_to_expiry_years"} and any(v <= 0 for v in out):
        raise ValueError(f"{field} scenario values must be positive")
    return out
