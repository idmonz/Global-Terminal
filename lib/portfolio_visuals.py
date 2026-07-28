from __future__ import annotations

from typing import Any

import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    px = None
    go = None


TEMPLATE = "plotly_dark"


def _empty_fig(title: str = "Data unavailable"):
    if go is None:
        return None
    fig = go.Figure()
    fig.update_layout(template=TEMPLATE, title=title, margin=dict(l=0, r=0, t=36, b=24))
    return fig


def _series(value: Any, name: str = "value") -> pd.Series:
    if isinstance(value, pd.Series):
        return pd.to_numeric(value, errors="coerce").dropna().rename(value.name or name)
    frame = pd.DataFrame(value)
    if frame.empty:
        return pd.Series(dtype=float, name=name)
    return pd.to_numeric(frame.iloc[:, 0], errors="coerce").dropna().rename(name)


def equity_curve_chart(equity_curve: Any):
    series = _series(equity_curve, "Equity Curve")
    if go is None or series.empty:
        return _empty_fig("Equity curve unavailable")
    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode="lines", name="Equity curve", line=dict(color="#38bdf8")))
    fig.update_layout(template=TEMPLATE, title="Equity Curve", margin=dict(l=0, r=0, t=36, b=24))
    return fig


def drawdown_chart(drawdown: Any):
    series = _series(drawdown, "Drawdown")
    if go is None or series.empty:
        return _empty_fig("Drawdown unavailable")
    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode="lines", fill="tozeroy", name="Drawdown", line=dict(color="#ef4444")))
    fig.update_layout(template=TEMPLATE, title="Drawdown", margin=dict(l=0, r=0, t=36, b=24), yaxis_tickformat=".0%")
    return fig


def underwater_chart(drawdown: Any):
    return drawdown_chart(drawdown)


def rolling_sharpe_chart(returns: Any, *, window: int = 63):
    series = _series(returns, "returns")
    if go is None or series.empty:
        return _empty_fig("Rolling Sharpe unavailable")
    sharpe = series.rolling(window).mean() / series.rolling(window).std().replace(0, pd.NA) * (252 ** 0.5)
    fig = go.Figure(go.Scatter(x=sharpe.index, y=sharpe.values, mode="lines", name="Rolling Sharpe", line=dict(color="#22c55e")))
    fig.update_layout(template=TEMPLATE, title="Rolling Sharpe", margin=dict(l=0, r=0, t=36, b=24))
    return fig


def rolling_volatility_chart(returns: Any, *, window: int = 63):
    series = _series(returns, "returns")
    if go is None or series.empty:
        return _empty_fig("Rolling volatility unavailable")
    vol = series.rolling(window).std() * (252 ** 0.5)
    fig = go.Figure(go.Scatter(x=vol.index, y=vol.values, mode="lines", name="Rolling Volatility", line=dict(color="#f59e0b")))
    fig.update_layout(template=TEMPLATE, title="Rolling Volatility", margin=dict(l=0, r=0, t=36, b=24), yaxis_tickformat=".0%")
    return fig


def monthly_returns_heatmap(returns: Any):
    series = _series(returns, "returns")
    if px is None or series.empty or not isinstance(series.index, pd.DatetimeIndex):
        return _empty_fig("Monthly heatmap unavailable")
    monthly = (1 + series).resample("ME").prod() - 1
    frame = monthly.to_frame("return")
    frame["year"] = frame.index.year
    frame["month"] = frame.index.strftime("%b")
    pivot = frame.pivot(index="year", columns="month", values="return")
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    pivot = pivot.reindex(columns=[m for m in month_order if m in pivot.columns])
    fig = px.imshow(pivot, template=TEMPLATE, color_continuous_scale="RdYlGn", aspect="auto", title="Monthly Returns")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=24))
    return fig


def risk_return_scatter(candidates: Any):
    frame = candidates.copy() if isinstance(candidates, pd.DataFrame) else pd.DataFrame(candidates)
    if px is None or frame.empty:
        return _empty_fig("Risk/return scatter unavailable")
    x = "annualized_volatility" if "annualized_volatility" in frame.columns else "volatility"
    y = "cagr" if "cagr" in frame.columns else "return"
    if x not in frame.columns:
        frame[x] = 0
    if y not in frame.columns:
        frame[y] = 0
    fig = px.scatter(frame, x=x, y=y, color="candidate" if "candidate" in frame.columns else None, size="sharpe" if "sharpe" in frame.columns else None, template=TEMPLATE, title="Risk / Return Research Candidates")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=24))
    return fig


def strategy_leaderboard_chart(leaderboard: Any):
    frame = leaderboard.copy() if isinstance(leaderboard, pd.DataFrame) else pd.DataFrame(leaderboard)
    if px is None or frame.empty:
        return _empty_fig("Strategy leaderboard unavailable")
    metric = "risk_adjusted_score" if "risk_adjusted_score" in frame.columns else "sharpe" if "sharpe" in frame.columns else frame.select_dtypes("number").columns[0]
    label = "candidate" if "candidate" in frame.columns else "name"
    fig = px.bar(frame.head(15), x=metric, y=label, orientation="h", template=TEMPLATE, title="Strategy Candidate Leaderboard")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=24), yaxis=dict(autorange="reversed"))
    return fig


def allocation_pie_or_bar(weights: dict[str, float] | pd.DataFrame):
    if isinstance(weights, pd.DataFrame):
        frame = weights.copy()
    else:
        frame = pd.DataFrame([{"asset": asset, "weight": weight} for asset, weight in (weights or {}).items()])
    if px is None or frame.empty:
        return _empty_fig("Allocation unavailable")
    fig = px.bar(frame, x="asset", y="weight", template=TEMPLATE, title="Allocation", text_auto=".1%")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=24), yaxis_tickformat=".0%")
    return fig


def allocation_timeline_chart(weights_timeline: pd.DataFrame):
    if px is None or weights_timeline is None or weights_timeline.empty:
        return _empty_fig("Allocation timeline unavailable")
    frame = weights_timeline.copy()
    frame["date"] = frame.index
    melted = frame.melt(id_vars="date", var_name="asset", value_name="weight")
    fig = px.area(melted, x="date", y="weight", color="asset", template=TEMPLATE, title="Allocation Timeline")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=24), yaxis_tickformat=".0%")
    return fig


def factor_exposure_radar_or_bar(exposures: Any):
    frame = exposures.copy() if isinstance(exposures, pd.DataFrame) else pd.DataFrame(exposures)
    if px is None or frame.empty:
        return _empty_fig("Factor exposure unavailable")
    value = "portfolio_beta" if "portfolio_beta" in frame.columns else "beta"
    fig = px.bar(frame, x="factor", y=value, template=TEMPLATE, title="Factor Exposure Proxies")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=24))
    return fig


def correlation_heatmap(returns: pd.DataFrame):
    if px is None or returns is None or returns.empty:
        return _empty_fig("Correlation heatmap unavailable")
    fig = px.imshow(returns.corr(), template=TEMPLATE, color_continuous_scale="RdBu", zmin=-1, zmax=1, title="Correlation Matrix")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=24))
    return fig


def risk_contribution_chart(contribution: Any):
    frame = contribution.copy() if isinstance(contribution, pd.DataFrame) else pd.DataFrame(contribution)
    if px is None or frame.empty:
        return _empty_fig("Risk contribution unavailable")
    fig = px.bar(frame, x="asset", y="risk_contribution", template=TEMPLATE, title="Risk Contribution")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=24), yaxis_tickformat=".0%")
    return fig


def return_contribution_chart(contribution: Any):
    frame = contribution.copy() if isinstance(contribution, pd.DataFrame) else pd.DataFrame(contribution)
    if px is None or frame.empty:
        return _empty_fig("Return contribution unavailable")
    fig = px.bar(frame, x="asset", y="return_contribution", template=TEMPLATE, title="Return Contribution")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=24), yaxis_tickformat=".0%")
    return fig


def monte_carlo_fan_chart(paths: pd.DataFrame):
    if go is None or paths is None or paths.empty:
        return _empty_fig("Forward paths unavailable")
    fig = go.Figure()
    for quantile, color in [(0.05, "#ef4444"), (0.25, "#f59e0b"), (0.50, "#38bdf8"), (0.75, "#22c55e"), (0.95, "#a78bfa")]:
        series = paths.quantile(quantile, axis=1)
        fig.add_trace(go.Scatter(x=series.index, y=series.values, mode="lines", name=f"p{int(quantile*100):02d}", line=dict(color=color)))
    fig.update_layout(template=TEMPLATE, title="Model-Estimated Forward Distribution", margin=dict(l=0, r=0, t=36, b=24))
    return fig


def forecast_distribution_chart(summary: dict[str, Any]):
    paths = summary.get("paths") if isinstance(summary, dict) else None
    return monte_carlo_fan_chart(paths)


def turnover_chart(turnover: Any):
    series = _series(turnover, "turnover")
    if go is None or series.empty:
        return _empty_fig("Turnover unavailable")
    fig = go.Figure(go.Bar(x=series.index, y=series.values, name="Turnover", marker_color="#38bdf8"))
    fig.update_layout(template=TEMPLATE, title="Rebalance Turnover", margin=dict(l=0, r=0, t=36, b=24), yaxis_tickformat=".0%")
    return fig


def strategy_comparison_dashboard(results: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for result in results:
        metrics = result.get("metrics", result)
        rows.append({"candidate": result.get("candidate", "Strategy candidate"), **metrics})
    leaderboard = pd.DataFrame(rows)
    return {
        "leaderboard": leaderboard,
        "leaderboard_chart": strategy_leaderboard_chart(leaderboard),
        "risk_return_chart": risk_return_scatter(leaderboard),
        "caveat": "Strategy comparison is historical research context, not advice.",
    }
