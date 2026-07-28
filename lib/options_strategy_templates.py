from __future__ import annotations

from typing import Any

from .options_payoff import covered_call_payoff, payoff_summary, protective_put_payoff, straddle_payoff, strangle_payoff, vertical_spread_payoff
from .options_advanced_payoffs import butterfly, calendar_spread, custom_multi_leg_payoff, diagonal_spread, iron_condor, ratio_spread
from .options_advanced_payoffs import butterfly, calendar_spread, custom_multi_leg_payoff, diagonal_spread, iron_condor, ratio_spread
from .options_advanced_payoffs import butterfly, calendar_spread, custom_multi_leg_payoff, diagonal_spread, iron_condor, ratio_spread
from .options_advanced_payoffs import butterfly, calendar_spread, custom_multi_leg_payoff, diagonal_spread, iron_condor, ratio_spread
from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE


def list_option_strategy_templates() -> list[dict[str, Any]]:
    return [
        {"template": "single_option", "description": "One call or put payoff profile from supplied premium.", "requires": ["option_type", "strike", "premium", "price_grid"]},
        {"template": "covered_call", "description": "Underlying plus a short call payoff profile, research-only.", "requires": ["underlying_cost", "call_strike", "call_premium", "price_grid"]},
        {"template": "protective_put", "description": "Underlying plus a long put payoff profile, research-only.", "requires": ["underlying_cost", "put_strike", "put_premium", "price_grid"]},
        {"template": "vertical_spread", "description": "Two-option same-expiry spread payoff profile, research-only.", "requires": ["option_type", "lower_strike", "upper_strike", "premiums", "price_grid"]},
        {"template": "straddle", "description": "Same-strike call and put payoff profile, research-only.", "requires": ["strike", "call_premium", "put_premium", "price_grid"]},
        {"template": "strangle", "description": "OTM call and put payoff profile, research-only.", "requires": ["call_strike", "put_strike", "premiums", "price_grid"]},
        {"template": "calendar_spread", "description": "Same-strike, different-expiry option payoff approximation, research-only.", "requires": ["strike", "near_premium", "far_premium", "price_grid"]},
        {"template": "diagonal_spread", "description": "Different-strike, different-expiry payoff approximation, research-only.", "requires": ["near_strike", "far_strike", "premiums", "price_grid"]},
        {"template": "butterfly", "description": "Three-strike limited-risk payoff template, research-only.", "requires": ["center_strike", "wing_width", "premiums", "price_grid"]},
        {"template": "iron_condor", "description": "Four-leg put/call spread payoff template, research-only.", "requires": ["strikes", "premiums", "price_grid"]},
        {"template": "ratio_spread", "description": "Ratio spread payoff template with tail-risk caveat, research-only.", "requires": ["long_strike", "short_strike", "short_quantity", "price_grid"]},
        {"template": "custom_multi_leg", "description": "User-supplied multi-leg payoff profile, research-only.", "requires": ["legs", "price_grid"]},
    ]


def build_strategy_payoff(template: str, payload: dict[str, Any]) -> dict[str, Any]:
    name = str(template or "single_option").lower()
    data = dict(payload or {})
    grid = [float(v) for v in data.get("price_grid", [])]
    if name == "single_option":
        legs = [{"option_type": data.get("option_type", "call"), "strike": data["strike"], "premium": data.get("premium", 0.0), "position": data.get("position", "long"), "contract_multiplier": data.get("contract_multiplier", 100.0)}]
        return {**payoff_summary(legs, grid), "strategy_template": "single_option"}
    if name == "covered_call":
        return covered_call_payoff(data["underlying_cost"], data["call_strike"], data.get("call_premium", 0.0), grid, data.get("shares", 100.0))
    if name == "protective_put":
        return protective_put_payoff(data["underlying_cost"], data["put_strike"], data.get("put_premium", 0.0), grid, data.get("shares", 100.0))
    if name == "vertical_spread":
        return vertical_spread_payoff(data.get("option_type", "call"), data["lower_strike"], data["upper_strike"], data.get("lower_premium", 0.0), data.get("upper_premium", 0.0), grid, contract_multiplier=data.get("contract_multiplier", 100.0), lower_position=data.get("lower_position", "long"))
    if name == "straddle":
        return straddle_payoff(data["strike"], data.get("call_premium", 0.0), data.get("put_premium", 0.0), grid, contract_multiplier=data.get("contract_multiplier", 100.0), position=data.get("position", "long"))
    if name == "strangle":
        return strangle_payoff(data["call_strike"], data["put_strike"], data.get("call_premium", 0.0), data.get("put_premium", 0.0), grid, contract_multiplier=data.get("contract_multiplier", 100.0), position=data.get("position", "long"))
    if name == "calendar_spread":
        return calendar_spread(data["strike"], data.get("near_premium", 0.0), data.get("far_premium", 0.0), grid, option_type=data.get("option_type", "call"), contract_multiplier=data.get("contract_multiplier", 100.0))
    if name == "diagonal_spread":
        return diagonal_spread(data["near_strike"], data["far_strike"], data.get("near_premium", 0.0), data.get("far_premium", 0.0), grid, option_type=data.get("option_type", "call"), contract_multiplier=data.get("contract_multiplier", 100.0))
    if name == "butterfly":
        return butterfly(data["center_strike"], data["wing_width"], data.get("lower_premium", 0.0), data.get("center_premium", 0.0), data.get("upper_premium", 0.0), grid, option_type=data.get("option_type", "call"), contract_multiplier=data.get("contract_multiplier", 100.0))
    if name == "iron_condor":
        return iron_condor(data["lower_put"], data["short_put"], data["short_call"], data["upper_call"], data.get("premiums", {}), grid, contract_multiplier=data.get("contract_multiplier", 100.0))
    if name == "ratio_spread":
        return ratio_spread(data["long_strike"], data["short_strike"], data.get("long_premium", 0.0), data.get("short_premium", 0.0), data.get("short_quantity", 2.0), grid, option_type=data.get("option_type", "call"), contract_multiplier=data.get("contract_multiplier", 100.0))
    if name == "custom_multi_leg":
        return custom_multi_leg_payoff(data.get("legs", []), grid)
    return {"ok": False, "error": "unknown_template", "templates": list_option_strategy_templates(), "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
