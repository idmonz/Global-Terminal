from __future__ import annotations

from typing import Any

from .options_pricing_inputs import RESEARCH_ONLY_OPTIONS_NOTICE
from .options_pricing_models import price_option
from .options_validation import validate_option_input


def _price_at_vol(base: dict[str, Any], volatility: float) -> float:
    data = {**base, "volatility": float(volatility)}
    return float(price_option(data)["price"])


def implied_volatility(input_data: dict[str, Any], market_price: float | None = None, *, lower: float = 1e-6, upper: float = 5.0, tolerance: float = 1e-8, max_iterations: int = 100) -> dict[str, Any]:
    base = dict(input_data or {})
    target = float(market_price if market_price is not None else base.get("premium")) if (market_price is not None or base.get("premium") is not None) else None
    if target is None:
        return {"ok": False, "converged": False, "implied_volatility": None, "error_reason": "market_price_or_premium_required", "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
    if target <= 0:
        return {"ok": False, "converged": False, "implied_volatility": None, "error_reason": "target_price_must_be_positive", "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
    base.setdefault("volatility", max(0.2, lower))
    try:
        inp = validate_option_input(base)
    except ValueError as exc:
        return {"ok": False, "converged": False, "implied_volatility": None, "error_reason": str(exc), "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
    base = inp.to_dict()
    low, high = float(lower), float(upper)
    try:
        p_low = _price_at_vol(base, low)
        p_high = _price_at_vol(base, high)
    except Exception as exc:
        return {"ok": False, "converged": False, "implied_volatility": None, "error_reason": f"pricing_failed: {exc}", "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
    if target < p_low - tolerance:
        return {"ok": False, "converged": False, "implied_volatility": None, "error_reason": "target_price_below_model_lower_bound", "bounds": {"lower_price": p_low, "upper_price": p_high}, "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
    while target > p_high and high < 20.0:
        high *= 2.0
        p_high = _price_at_vol(base, high)
    if target > p_high + tolerance:
        return {"ok": False, "converged": False, "implied_volatility": None, "error_reason": "target_price_above_model_upper_bound", "bounds": {"lower_price": p_low, "upper_price": p_high}, "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
    mid = (low + high) / 2.0
    p_mid = _price_at_vol(base, mid)
    for iteration in range(1, max_iterations + 1):
        mid = (low + high) / 2.0
        p_mid = _price_at_vol(base, mid)
        diff = p_mid - target
        if abs(diff) <= tolerance:
            return {"ok": True, "converged": True, "implied_volatility": float(mid), "model_price": p_mid, "target_price": target, "iterations": iteration, "error_reason": "", "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
        if p_mid > target:
            high = mid
        else:
            low = mid
    return {"ok": False, "converged": False, "implied_volatility": float(mid), "model_price": p_mid, "target_price": target, "iterations": max_iterations, "error_reason": "max_iterations_reached", "notice": RESEARCH_ONLY_OPTIONS_NOTICE, "research_only": True}
