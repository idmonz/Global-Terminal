from __future__ import annotations

from typing import Any

from .options_chain_schema import GOAL12B_RESEARCH_ONLY_NOTICE
from .options_payoff import payoff_summary, single_option_payoff

VALID_POSITIONS = {"long", "short"}
VALID_TYPES = {"call", "put"}


def validate_payoff_leg(leg: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if str(leg.get("option_type", "")).lower() not in VALID_TYPES:
        errors.append("invalid_option_type")
    if str(leg.get("position", "long")).lower() not in VALID_POSITIONS:
        errors.append("invalid_position")
    for field in ["strike", "quantity", "contract_multiplier"]:
        try:
            if float(leg.get(field, 1.0)) <= 0:
                errors.append(f"non_positive_{field}")
        except Exception:
            errors.append(f"invalid_{field}")
    try:
        if float(leg.get("premium", 0.0)) < 0:
            errors.append("negative_premium")
    except Exception:
        errors.append("invalid_premium")
    return {"ok": not errors, "errors": errors, "research_only": True}


def validate_payoff_grid(price_grid: list[float]) -> list[float]:
    if not price_grid:
        raise ValueError("price_grid_required")
    out = [float(v) for v in price_grid]
    if any(v <= 0 for v in out):
        raise ValueError("price_grid_values_must_be_positive")
    return sorted(out)


def custom_multi_leg_payoff(legs: list[dict[str, Any]], price_grid: list[float], *, strategy_template: str = "custom_multi_leg", expiry_caveat: str = "expiry_handled_as_expiry_payoff") -> dict[str, Any]:
    grid = validate_payoff_grid(price_grid)
    errors = []
    normalized = []
    for i, leg in enumerate(legs, start=1):
        check = validate_payoff_leg(leg)
        if not check["ok"]:
            errors.append({"leg_index": i, "errors": check["errors"]})
        normalized.append({**leg, "option_type": str(leg.get("option_type", "call")).lower(), "position": str(leg.get("position", "long")).lower(), "quantity": float(leg.get("quantity", 1.0)), "contract_multiplier": float(leg.get("contract_multiplier", 100.0)), "premium": float(leg.get("premium", 0.0))})
    if errors:
        return {"ok": False, "errors": errors, "notice": GOAL12B_RESEARCH_ONLY_NOTICE, "research_only": True}
    summary = payoff_summary(normalized, grid)
    pnls = [row["total_pnl"] for row in summary["table"]]
    quantity_by_type = {}
    for leg in normalized:
        key = (leg["option_type"], leg["position"])
        quantity_by_type[str(key)] = quantity_by_type.get(str(key), 0.0) + leg["quantity"]
    unlimited = any(leg["position"] == "short" and leg["option_type"] == "call" for leg in normalized)
    return {**summary, "ok": True, "strategy_template": strategy_template, "net_debit_or_credit": summary.get("net_debit_positive_or_credit_negative"), "grid_limited_max_gain": max(pnls) if pnls else None, "grid_limited_max_loss": min(pnls) if pnls else None, "analytic_max_gain_loss": "available_only_for_simple_defined_templates", "unlimited_loss_caveat": unlimited, "expiry_caveat": expiry_caveat, "quantity_by_type": quantity_by_type, "notice": GOAL12B_RESEARCH_ONLY_NOTICE}


def calendar_spread(strike: float, near_premium: float, far_premium: float, price_grid: list[float], *, option_type: str = "call", contract_multiplier: float = 100.0) -> dict[str, Any]:
    legs = [
        {"option_type": option_type, "strike": strike, "premium": near_premium, "position": "short", "contract_multiplier": contract_multiplier},
        {"option_type": option_type, "strike": strike, "premium": far_premium, "position": "long", "contract_multiplier": contract_multiplier},
    ]
    return custom_multi_leg_payoff(legs, price_grid, strategy_template="calendar_spread", expiry_caveat="calendar payoff is expiry-simplified; pre-expiry value needs term-structure inputs")


def diagonal_spread(near_strike: float, far_strike: float, near_premium: float, far_premium: float, price_grid: list[float], *, option_type: str = "call", contract_multiplier: float = 100.0) -> dict[str, Any]:
    legs = [
        {"option_type": option_type, "strike": near_strike, "premium": near_premium, "position": "short", "contract_multiplier": contract_multiplier},
        {"option_type": option_type, "strike": far_strike, "premium": far_premium, "position": "long", "contract_multiplier": contract_multiplier},
    ]
    return custom_multi_leg_payoff(legs, price_grid, strategy_template="diagonal_spread", expiry_caveat="diagonal payoff is expiry-simplified; expiries differ and residual time value is caveated")


def butterfly(center_strike: float, wing_width: float, lower_premium: float, center_premium: float, upper_premium: float, price_grid: list[float], *, option_type: str = "call", contract_multiplier: float = 100.0) -> dict[str, Any]:
    legs = [
        {"option_type": option_type, "strike": center_strike - wing_width, "premium": lower_premium, "position": "long", "contract_multiplier": contract_multiplier},
        {"option_type": option_type, "strike": center_strike, "premium": center_premium, "position": "short", "quantity": 2, "contract_multiplier": contract_multiplier},
        {"option_type": option_type, "strike": center_strike + wing_width, "premium": upper_premium, "position": "long", "contract_multiplier": contract_multiplier},
    ]
    return custom_multi_leg_payoff(legs, price_grid, strategy_template="butterfly")


def iron_condor(lower_put: float, short_put: float, short_call: float, upper_call: float, premiums: dict[str, float], price_grid: list[float], *, contract_multiplier: float = 100.0) -> dict[str, Any]:
    legs = [
        {"option_type": "put", "strike": lower_put, "premium": premiums.get("lower_put", 0.0), "position": "long", "contract_multiplier": contract_multiplier},
        {"option_type": "put", "strike": short_put, "premium": premiums.get("short_put", 0.0), "position": "short", "contract_multiplier": contract_multiplier},
        {"option_type": "call", "strike": short_call, "premium": premiums.get("short_call", 0.0), "position": "short", "contract_multiplier": contract_multiplier},
        {"option_type": "call", "strike": upper_call, "premium": premiums.get("upper_call", 0.0), "position": "long", "contract_multiplier": contract_multiplier},
    ]
    return custom_multi_leg_payoff(legs, price_grid, strategy_template="iron_condor")


def ratio_spread(long_strike: float, short_strike: float, long_premium: float, short_premium: float, short_quantity: float, price_grid: list[float], *, option_type: str = "call", contract_multiplier: float = 100.0) -> dict[str, Any]:
    legs = [
        {"option_type": option_type, "strike": long_strike, "premium": long_premium, "position": "long", "contract_multiplier": contract_multiplier},
        {"option_type": option_type, "strike": short_strike, "premium": short_premium, "position": "short", "quantity": short_quantity, "contract_multiplier": contract_multiplier},
    ]
    result = custom_multi_leg_payoff(legs, price_grid, strategy_template="ratio_spread")
    result["ratio_spread_caveat"] = "Ratio spreads can have asymmetric or unlimited tails; metrics are grid-limited unless analytically stated."
    return result
