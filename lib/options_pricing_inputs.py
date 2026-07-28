from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

OptionType = Literal["call", "put"]
OptionModel = Literal["black_scholes", "black_76", "garman_kohlhagen"]

RESEARCH_ONLY_OPTIONS_NOTICE = (
    "Options and model outputs are research calculations only. They are not investment advice, "
    "trading recommendations, trade approvals, or execution instructions."
)


@dataclass(frozen=True)
class OptionPricingInput:
    option_type: str
    underlying_price: float
    strike: float
    time_to_expiry_years: float
    risk_free_rate: float
    volatility: float
    model: str = "black_scholes"
    dividend_yield: float = 0.0
    carry_rate: float | None = None
    futures_price: float | None = None
    foreign_rate: float | None = None
    domestic_rate: float | None = None
    contract_multiplier: float = 100.0
    premium: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_option_type(option_type: str) -> str:
    value = str(option_type or "").strip().lower()
    if value not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    return value


def normalize_model(model: str) -> str:
    value = str(model or "black_scholes").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {"bs": "black_scholes", "bsm": "black_scholes", "black76": "black_76", "black_76": "black_76", "gk": "garman_kohlhagen"}
    value = aliases.get(value, value)
    if value not in {"black_scholes", "black_76", "garman_kohlhagen"}:
        raise ValueError("model must be black_scholes, black_76, or garman_kohlhagen")
    return value


def build_option_input(**kwargs: Any) -> OptionPricingInput:
    data = dict(kwargs)
    data["option_type"] = normalize_option_type(data.get("option_type", "call"))
    data["model"] = normalize_model(data.get("model", "black_scholes"))
    return OptionPricingInput(**data)
