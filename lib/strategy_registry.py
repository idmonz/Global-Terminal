from __future__ import annotations

from itertools import combinations
from typing import Any

import pandas as pd

from .compliance import contains_forbidden_language


def _definition(name: str, category: str, description: str, required_data: list[str], signals: list[str], weighting: str, rebalance: str, controls: list[str], caveats: list[str], available: bool = True, gaps: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "category": category,
        "description": description,
        "required_data": required_data,
        "signals_used": signals,
        "weighting_method": weighting,
        "rebalance_frequency": rebalance,
        "risk_controls": controls,
        "caveats": caveats,
        "is_available": available,
        "data_gaps": gaps or [],
    }


def build_strategy_registry() -> list[dict[str, Any]]:
    return [
        _definition("Equal Weight Baseline", "baseline", "Simple diversified research baseline.", ["ticker list"], [], "equal_weight", "none", ["max asset cap optional"], ["No factor or timing model."]),
        _definition("Inverse Volatility", "risk", "Weights lower-volatility assets more heavily using historical volatility.", ["price history"], ["low_volatility"], "inverse_volatility", "monthly", ["max asset cap"], ["Uses realized volatility as a proxy."]),
        _definition("Risk Parity Proxy", "risk", "Approximates balanced risk contribution with inverse volatility.", ["price history"], ["low_volatility"], "risk_parity_proxy", "monthly", ["max asset cap"], ["Not a full risk-parity optimizer."]),
        _definition("Momentum Rotation", "alpha", "Ranks assets by multi-horizon momentum evidence.", ["price history"], ["momentum"], "signal_rank", "monthly", ["turnover cap", "max asset cap"], ["Past momentum can reverse."]),
        _definition("Trend Following Basket", "alpha", "Uses moving-average and breakout proxies.", ["price history"], ["trend"], "trend_score", "monthly", ["cash sleeve optional"], ["Whipsaw risk can be material."]),
        _definition("Value + Quality Tilt", "alpha", "Combines valuation and quality proxies where fundamentals exist.", ["fundamentals"], ["value", "quality"], "factor_tilt", "quarterly", ["missing-data cap"], ["Fundamental coverage may be incomplete."]),
        _definition("Low Volatility Defensive", "risk", "Emphasizes lower realized volatility and smaller drawdown profiles.", ["price history"], ["low_volatility"], "defensive_tilt", "monthly", ["max asset cap"], ["Can lag in high-beta rallies."]),
        _definition("Macro Regime Rotation", "macro", "Tilts exposure by rates, USD, oil, gold, volatility, and breadth regimes.", ["macro proxies"], ["macro_rotation"], "regime_tilt", "monthly", ["scenario caveat"], ["Regime labels are heuristic."]),
        _definition("Crypto Derivatives Stress-Aware", "crypto", "Uses funding, open interest, taker imbalance, and liquidation pressure proxies.", ["crypto derivatives"], ["crypto_derivatives"], "stress_aware", "weekly", ["crowding cap"], ["Estimated pressure is proxy-based in free mode."]),
        _definition("News-Aware Event Risk", "osint", "Uses event severity and source/freshness context to lower concentration in affected assets.", ["news events"], ["news_impact"], "event_risk_tilt", "weekly", ["source gap badge"], ["News impact is heuristic and source-dependent."]),
        _definition("Volatility Targeted Portfolio", "risk", "Scales risky exposure toward a target realized volatility.", ["price history"], ["low_volatility"], "volatility_target", "monthly", ["cash sleeve"], ["Target volatility can fail during gaps."]),
        _definition("Max Diversification Proxy", "risk", "Balances inverse volatility with correlation dispersion.", ["price history"], ["correlation"], "max_diversification_proxy", "monthly", ["max asset cap"], ["Correlation is historical and unstable."]),
        _definition("Min Variance Proxy", "risk", "Seeks lower ex-post variance under no-short default constraints.", ["price history"], ["covariance"], "min_variance_proxy", "monthly", ["no-short default", "max asset cap"], ["Optimizer can be sensitive to estimates."]),
        _definition("Multi-Factor Blend", "alpha", "Combines momentum, value, quality, low volatility, carry, and macro proxies.", ["price history", "optional fundamentals"], ["momentum", "value", "quality", "low_volatility", "carry", "macro_rotation"], "multi_signal_score", "monthly", ["max asset cap", "data-gap penalty"], ["Signal weights are research assumptions."]),
        _definition("Defensive Crisis Basket", "risk", "Combines defensive regime, USD, duration, gold, and stress proxies.", ["price history", "macro proxies"], ["defensive_regime", "macro_rotation"], "defensive_proxy", "monthly", ["cash sleeve optional"], ["Crisis relationships can break down."]),
    ]


def get_strategy_definition(name: str) -> dict[str, Any] | None:
    normalized = str(name).lower()
    return next((item for item in build_strategy_registry() if item["name"].lower() == normalized), None)


def validate_strategy_definition(definition: dict[str, Any]) -> tuple[bool, list[str]]:
    required = {"name", "category", "description", "required_data", "signals_used", "weighting_method", "rebalance_frequency", "risk_controls", "caveats", "is_available", "data_gaps"}
    issues = [f"Missing {key}" for key in sorted(required - set(definition))]
    text = " ".join(str(definition.get(key, "")) for key in ["name", "description", "weighting_method"])
    if contains_forbidden_language(text, allow_disclosure=False):
        issues.append("Restricted directive language detected.")
    return not issues, issues


def build_strategy_candidate_set(available_data: set[str] | None = None) -> pd.DataFrame:
    available_data = available_data or set()
    rows = []
    for definition in build_strategy_registry():
        missing = [item for item in definition["required_data"] if item not in available_data and item not in {"ticker list"}]
        row = {**definition, "is_available": definition["is_available"] and not missing, "data_gaps": definition["data_gaps"] + missing}
        rows.append(row)
    return pd.DataFrame(rows)


def generate_alpha_combinations(families: list[str] | None = None, *, max_size: int = 3) -> list[dict[str, Any]]:
    families = families or ["momentum", "trend", "low_volatility", "value", "quality", "carry", "macro_rotation", "news_impact"]
    output = []
    for size in range(1, min(max_size, len(families)) + 1):
        for combo in combinations(families, size):
            output.append({"name": " + ".join(part.replace("_", " ").title() for part in combo), "families": list(combo), "description": "Alpha combination for neutral research comparison.", "caveat": "Signal combination is a research candidate."})
    return output


def rank_strategy_candidates_by_backtest(results: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for result in results:
        metrics = result.get("metrics", result)
        rows.append(
            {
                "candidate": result.get("candidate") or result.get("strategy") or "Strategy candidate",
                "cagr": metrics.get("cagr"),
                "sharpe": metrics.get("sharpe"),
                "max_drawdown": metrics.get("max_drawdown"),
                "calmar": metrics.get("calmar"),
                "transaction_cost_estimate": metrics.get("transaction_cost_estimate", 0.0),
                "caveat": "Backtest-ranked bundle; past performance does not guarantee future results.",
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values(["sharpe", "calmar"], ascending=False, na_position="last")


def rank_strategy_candidates_by_risk_adjusted_score(candidates: pd.DataFrame | list[dict[str, Any]]) -> pd.DataFrame:
    frame = candidates.copy() if isinstance(candidates, pd.DataFrame) else pd.DataFrame(candidates)
    if frame.empty:
        return frame
    for column in ["sharpe", "calmar", "cagr", "max_drawdown"]:
        if column not in frame.columns:
            frame[column] = 0.0
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    frame["risk_adjusted_score"] = (frame["sharpe"].clip(-2, 4) + frame["calmar"].clip(-2, 4) + frame["cagr"].clip(-1, 1) * 2 - frame["max_drawdown"].abs().clip(0, 1)) * 25
    frame["risk_adjusted_score"] = frame["risk_adjusted_score"].clip(0, 100).round(1)
    return frame.sort_values("risk_adjusted_score", ascending=False)
