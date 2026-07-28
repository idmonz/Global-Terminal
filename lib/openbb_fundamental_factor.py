from __future__ import annotations

from typing import Any

try:
    import numpy as np
    import pandas as pd
except Exception:  # pragma: no cover
    np = None
    pd = None

from .data_router import request_financials


def _score(value: Any, *, center: float, scale: float, inverse: bool = False) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    raw = 50.0 + (number - center) / scale * 50.0
    if inverse:
        raw = 100.0 - raw
    return round(max(0.0, min(100.0, raw)), 1)


def _latest_dict(result: Any) -> dict[str, Any]:
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    if pd is None or data is None or getattr(data, "empty", True):
        return {}
    frame = data.dropna(how="all")
    return frame.iloc[-1].to_dict() if not frame.empty else {}


def get_value_factor_data(symbol: str, *, source_mode: str = "auto") -> dict[str, Any]:
    ratios = request_financials(symbol, statement="ratios", source_mode=source_mode, allow_estimates=True, allow_proxy=True)
    latest = _latest_dict(ratios)
    scores = [
        _score(latest.get("pe") or latest.get("trailing_pe"), center=18, scale=18, inverse=True),
        _score(latest.get("pb") or latest.get("price_to_book"), center=3, scale=3, inverse=True),
        _score(latest.get("ps") or latest.get("price_to_sales"), center=4, scale=4, inverse=True),
    ]
    usable = [score for score in scores if score is not None]
    return {"symbol": symbol.upper(), "value_score": round(float(np.mean(usable)), 1) if usable and np is not None else 0.0, "raw": latest, "result": ratios, "data_gaps": ratios.data_gaps}


def get_quality_factor_data(symbol: str, *, source_mode: str = "auto") -> dict[str, Any]:
    ratios = request_financials(symbol, statement="ratios", source_mode=source_mode, allow_estimates=True, allow_proxy=True)
    latest = _latest_dict(ratios)
    scores = [
        _score(latest.get("roe"), center=0.12, scale=0.18),
        _score(latest.get("roa"), center=0.05, scale=0.10),
        _score(latest.get("debt_to_equity"), center=1.0, scale=1.0, inverse=True),
    ]
    usable = [score for score in scores if score is not None]
    return {"symbol": symbol.upper(), "quality_score": round(float(np.mean(usable)), 1) if usable and np is not None else 0.0, "raw": latest, "result": ratios, "data_gaps": ratios.data_gaps}


def get_growth_factor_data(symbol: str, *, source_mode: str = "auto") -> dict[str, Any]:
    income = request_financials(symbol, statement="income", source_mode=source_mode)
    data = getattr(income, "data", None)
    growth = None
    if pd is not None and data is not None and not getattr(data, "empty", True):
        col = "revenue" if "revenue" in data.columns else "net_income" if "net_income" in data.columns else None
        if col and len(data[col].dropna()) >= 2:
            series = pd.to_numeric(data[col], errors="coerce").dropna()
            growth = float(series.pct_change().iloc[-1])
    return {"symbol": symbol.upper(), "growth_score": _score(growth, center=0.05, scale=0.20) if growth is not None else 0.0, "growth_rate": growth, "result": income, "data_gaps": income.data_gaps}


def get_profitability_factor_data(symbol: str, *, source_mode: str = "auto") -> dict[str, Any]:
    income = request_financials(symbol, statement="income", source_mode=source_mode)
    latest = _latest_dict(income)
    revenue = latest.get("revenue") or latest.get("total_revenue")
    margin = None
    try:
        margin = float(latest.get("net_income")) / float(revenue) if revenue else None
    except Exception:
        margin = None
    return {"symbol": symbol.upper(), "profitability_score": _score(margin, center=0.10, scale=0.20) if margin is not None else 0.0, "net_margin": margin, "result": income, "data_gaps": income.data_gaps}


def build_fundamental_factor_scores(symbol: str, *, source_mode: str = "auto") -> dict[str, Any]:
    value = get_value_factor_data(symbol, source_mode=source_mode)
    quality = get_quality_factor_data(symbol, source_mode=source_mode)
    growth = get_growth_factor_data(symbol, source_mode=source_mode)
    profitability = get_profitability_factor_data(symbol, source_mode=source_mode)
    gaps = list(value["data_gaps"]) + list(quality["data_gaps"]) + list(growth["data_gaps"]) + list(profitability["data_gaps"])
    coverage = max(0.0, 100.0 - min(100.0, len(gaps) * 10.0))
    return {
        "symbol": symbol.upper(),
        "value_score": value["value_score"],
        "quality_score": quality["quality_score"],
        "growth_score": growth["growth_score"],
        "profitability_score": profitability["profitability_score"],
        "data_quality_score": round(coverage, 1),
        "data_gaps": gaps,
        "caveat": "Fundamental factor scores use available reported/provider fields only; missing estimates are not fabricated.",
    }
