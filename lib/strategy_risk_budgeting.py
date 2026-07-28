from __future__ import annotations

from typing import Any

import pandas as pd


def compute_strategy_risk_contributions(strategy_returns: pd.DataFrame, weights: Any | None = None) -> pd.DataFrame:
    if strategy_returns is None or strategy_returns.empty:
        return pd.DataFrame(columns=["strategy", "weight", "volatility", "risk_contribution"])
    vols = strategy_returns.std(ddof=0).fillna(0)
    if weights is None:
        weight_series = pd.Series(1 / len(strategy_returns.columns), index=strategy_returns.columns)
    elif isinstance(weights, pd.DataFrame):
        weight_series = weights.set_index("strategy")["weight"].reindex(strategy_returns.columns).fillna(0)
    else:
        weight_series = pd.Series(weights).reindex(strategy_returns.columns).fillna(0)
    raw = (vols * weight_series).clip(lower=0)
    denom = float(raw.sum()) or 1.0
    return pd.DataFrame({"strategy": strategy_returns.columns, "weight": weight_series.values, "volatility": vols.values, "risk_contribution": (raw / denom).values})


def build_strategy_risk_budget(strategy_returns: pd.DataFrame, weights: Any | None = None) -> dict[str, Any]:
    table = compute_strategy_risk_contributions(strategy_returns, weights)
    concentration = float(table["risk_contribution"].max()) if not table.empty else 0.0
    return {"table": table, "risk_concentration": round(concentration, 4), "caveat": "Risk budgets are estimated from historical/proxy returns."}
