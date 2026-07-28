from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


ATTRIBUTION_CAVEAT = "Attribution is a historical/proxy estimate for research only."


def compute_asset_return_contribution(asset_returns: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    if asset_returns is None or asset_returns.empty:
        return pd.DataFrame(columns=["asset", "weight", "total_return", "return_contribution", "caveat"])
    rows = []
    for asset in asset_returns.columns:
        weight = float(weights.get(asset, 0.0))
        total_return = float((1.0 + asset_returns[asset].dropna()).prod() - 1.0)
        rows.append({"asset": asset, "weight": weight, "total_return": total_return, "return_contribution": weight * total_return, "caveat": ATTRIBUTION_CAVEAT})
    return pd.DataFrame(rows).sort_values("return_contribution", ascending=False)


def compute_risk_contribution(asset_returns: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    if asset_returns is None or asset_returns.empty:
        return pd.DataFrame(columns=["asset", "risk_contribution", "caveat"])
    assets = [asset for asset in asset_returns.columns if asset in weights]
    frame = asset_returns[assets].fillna(0.0)
    vector = np.array([weights[asset] for asset in assets], dtype=float)
    vector = vector / vector.sum() if vector.sum() else vector
    cov = frame.cov().to_numpy()
    port_var = float(vector.T @ cov @ vector)
    marginal = cov @ vector / np.sqrt(port_var) if port_var > 0 else np.zeros(len(vector))
    contribution = vector * marginal
    total = contribution.sum()
    pct = contribution / total if total else contribution
    return pd.DataFrame({"asset": assets, "weight": vector, "risk_contribution": pct, "caveat": ATTRIBUTION_CAVEAT})


def compute_drawdown_contribution(asset_returns: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    if asset_returns is None or asset_returns.empty:
        return pd.DataFrame(columns=["asset", "drawdown_contribution", "caveat"])
    portfolio = sum(asset_returns[asset].fillna(0.0) * float(weights.get(asset, 0.0)) for asset in asset_returns.columns)
    equity = (1.0 + portfolio).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    trough = drawdown.idxmin() if not drawdown.empty else None
    rows = []
    for asset in asset_returns.columns:
        contribution = float(asset_returns.loc[:trough, asset].fillna(0.0).sum() * weights.get(asset, 0.0)) if trough is not None else 0.0
        rows.append({"asset": asset, "drawdown_contribution": contribution, "caveat": ATTRIBUTION_CAVEAT})
    return pd.DataFrame(rows).sort_values("drawdown_contribution")


def _group_contribution(return_contribution: pd.DataFrame, metadata: dict[str, dict[str, Any]], key: str) -> pd.DataFrame:
    if return_contribution is None or return_contribution.empty:
        return pd.DataFrame(columns=[key, "return_contribution", "caveat"])
    frame = return_contribution.copy()
    frame[key] = frame["asset"].map(lambda asset: metadata.get(asset, {}).get(key, "Unclassified"))
    grouped = frame.groupby(key)["return_contribution"].sum().reset_index()
    grouped["caveat"] = ATTRIBUTION_CAVEAT
    return grouped.sort_values("return_contribution", ascending=False)


def compute_sector_contribution(return_contribution: pd.DataFrame, metadata: dict[str, dict[str, Any]] | None = None) -> pd.DataFrame:
    return _group_contribution(return_contribution, metadata or {}, "sector")


def compute_asset_class_contribution(return_contribution: pd.DataFrame, metadata: dict[str, dict[str, Any]] | None = None) -> pd.DataFrame:
    return _group_contribution(return_contribution, metadata or {}, "asset_class")


def compute_rebalance_turnover(weights_timeline: pd.DataFrame) -> pd.DataFrame:
    if weights_timeline is None or weights_timeline.empty:
        return pd.DataFrame(columns=["date", "turnover", "caveat"])
    diff = weights_timeline.diff().abs().sum(axis=1) / 2.0
    return pd.DataFrame({"date": diff.index, "turnover": diff.values, "caveat": ATTRIBUTION_CAVEAT})


def build_attribution_report(asset_returns: pd.DataFrame, weights: dict[str, float], *, metadata: dict[str, dict[str, Any]] | None = None, weights_timeline: pd.DataFrame | None = None) -> dict[str, Any]:
    returns = compute_asset_return_contribution(asset_returns, weights)
    risk = compute_risk_contribution(asset_returns, weights)
    drawdown = compute_drawdown_contribution(asset_returns, weights)
    return {
        "return_contribution": returns,
        "risk_contribution": risk,
        "drawdown_contribution": drawdown,
        "sector_contribution": compute_sector_contribution(returns, metadata),
        "asset_class_contribution": compute_asset_class_contribution(returns, metadata),
        "turnover": compute_rebalance_turnover(weights_timeline if weights_timeline is not None else pd.DataFrame()),
        "top_contributors": returns.head(5).to_dict(orient="records") if not returns.empty else [],
        "top_detractors": returns.tail(5).to_dict(orient="records") if not returns.empty else [],
        "risk_concentration": risk.sort_values("risk_contribution", ascending=False).head(5).to_dict(orient="records") if not risk.empty else [],
        "caveat": ATTRIBUTION_CAVEAT,
    }
