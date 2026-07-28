from __future__ import annotations

from typing import Any

import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    px = None
    go = None


def _safe_figure(title: str):
    if go is None:
        return {"title": title, "figure": None, "caveat": "Plotly unavailable."}
    fig = go.Figure()
    fig.update_layout(template="plotly_dark", title=title, margin=dict(l=8, r=8, t=42, b=24))
    return fig


def strategy_ensemble_equity_curve(returns: pd.Series):
    fig = _safe_figure("Strategy Ensemble Equity Curve")
    if hasattr(fig, "add_scatter") and returns is not None and not returns.empty:
        curve = (1 + returns.fillna(0)).cumprod()
        fig.add_scatter(x=curve.index, y=curve.values, mode="lines", name="ensemble")
    return fig


def strategy_ensemble_drawdown_chart(returns: pd.Series):
    fig = _safe_figure("Strategy Ensemble Drawdown")
    if hasattr(fig, "add_scatter") and returns is not None and not returns.empty:
        curve = (1 + returns.fillna(0)).cumprod()
        drawdown = curve / curve.cummax() - 1
        fig.add_scatter(x=drawdown.index, y=drawdown.values, mode="lines", name="drawdown")
    return fig


def strategy_regime_heatmap(table: pd.DataFrame):
    if px is None or table is None or table.empty:
        return _safe_figure("Strategy Regime Heatmap")
    pivot = table.pivot_table(index="strategy", columns="regime", values="mean_return", aggfunc="mean")
    return px.imshow(pivot, template="plotly_dark", title="Strategy Regime Heatmap")


def strategy_correlation_cluster_heatmap(correlation: pd.DataFrame):
    if px is None or correlation is None or correlation.empty:
        return _safe_figure("Strategy Correlation Cluster")
    return px.imshow(correlation, template="plotly_dark", title="Strategy Correlation Cluster")


def walk_forward_decay_chart(windows: pd.DataFrame):
    if px is None or windows is None or windows.empty:
        return _safe_figure("Walk-Forward Decay")
    y = "oos_score" if "oos_score" in windows.columns else windows.columns[-1]
    return px.line(windows.reset_index(), x=windows.reset_index().columns[0], y=y, template="plotly_dark", title="Walk-Forward Decay")


def oos_vs_is_scatter(frame: pd.DataFrame):
    if px is None or frame is None or frame.empty:
        return _safe_figure("OOS vs IS")
    return px.scatter(frame, x="is_score", y="oos_score", template="plotly_dark", title="OOS vs IS")


def strategy_risk_budget_chart(table: pd.DataFrame):
    if px is None or table is None or table.empty:
        return _safe_figure("Strategy Risk Budget")
    return px.bar(table, x="strategy", y="risk_contribution", template="plotly_dark", title="Strategy Risk Budget")


def forward_distribution_comparison(distributions: dict[str, Any]):
    fig = _safe_figure("Forward Distribution Comparison")
    if hasattr(fig, "add_histogram"):
        for name, values in (distributions or {}).items():
            series = pd.Series(values).dropna()
            if not series.empty:
                fig.add_histogram(x=series, name=name, opacity=0.65)
    return fig


def strategy_score_radar(scores: dict[str, float]):
    fig = _safe_figure("Strategy Score Radar")
    if hasattr(fig, "add_trace") and scores:
        fig.add_trace(go.Scatterpolar(r=list(scores.values()), theta=list(scores.keys()), fill="toself", name="score"))
    return fig
