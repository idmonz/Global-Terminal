from __future__ import annotations

from typing import Any

import pandas as pd


CORRELATION_CAVEAT = "Strategy correlation is historical research context and can change materially."


def _returns_frame(value: Any) -> pd.DataFrame:
    frame = value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame(value)
    return frame.apply(pd.to_numeric, errors="coerce").dropna(how="all")


def compute_strategy_return_correlation(strategy_returns: Any) -> pd.DataFrame:
    frame = _returns_frame(strategy_returns)
    if frame.empty:
        return pd.DataFrame()
    output = frame.corr()
    output.attrs["caveat"] = CORRELATION_CAVEAT
    return output


def compute_strategy_drawdown_correlation(strategy_returns: Any) -> pd.DataFrame:
    frame = _returns_frame(strategy_returns)
    if frame.empty:
        return pd.DataFrame()
    equity = (1.0 + frame.fillna(0.0)).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    output = drawdown.corr()
    output.attrs["caveat"] = CORRELATION_CAVEAT
    return output


def build_strategy_correlation_heatmap_payload(strategy_returns: Any) -> dict[str, Any]:
    return_corr = compute_strategy_return_correlation(strategy_returns)
    drawdown_corr = compute_strategy_drawdown_correlation(strategy_returns)
    clusters = []
    if not return_corr.empty:
        for name in return_corr.columns:
            peers = return_corr[name].drop(labels=[name], errors="ignore")
            closest = peers.sort_values(ascending=False).head(3).index.tolist()
            clusters.append({"strategy": name, "closest_peers": closest, "diversification_score": float((1.0 - peers.mean()) if not peers.empty else 0.0)})
    return {
        "return_correlation": return_corr,
        "drawdown_correlation": drawdown_corr,
        "clusters": pd.DataFrame(clusters),
        "caveat": CORRELATION_CAVEAT,
    }
