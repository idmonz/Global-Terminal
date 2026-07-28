from __future__ import annotations

from typing import Any

from .data_status import error_result, ok_result

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    px = None
    go = None


def _frame(value: Any):
    if pd is None:
        return value or []
    if value is None:
        return pd.DataFrame()
    if hasattr(value, "copy") and hasattr(value, "columns"):
        return value.copy()
    if isinstance(value, list):
        return pd.DataFrame(value)
    if isinstance(value, dict):
        return pd.DataFrame([value])
    return pd.DataFrame()


def _plot_frame(value: Any):
    frame = _frame(value)
    if pd is None or frame is None or getattr(frame, "empty", True):
        return frame
    out = frame.copy()
    if out.index.name or not isinstance(out.index, pd.RangeIndex):
        out = out.reset_index()
        out = out.rename(columns={out.columns[0]: "period"})
    if "period" not in out.columns:
        out.insert(0, "period", range(len(out)))
    return out


def _empty(name: str, frame=None, message: str = "Required real data is unavailable."):
    return None, frame if frame is not None else _frame(None), error_result(source=name, provider="financial_charts", error=message, coverage="data gap")


def _finish(fig, title: str):
    fig.update_layout(
        template="plotly_dark",
        title=title,
        paper_bgcolor="#020617",
        plot_bgcolor="#020617",
        margin=dict(l=0, r=0, t=42, b=28),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def _numeric_columns(frame, candidates: list[str]) -> list[str]:
    return [col for col in candidates if col in getattr(frame, "columns", []) and frame[col].notna().any()]


def revenue_net_income_chart(income: Any = None):
    frame = _plot_frame(income)
    if px is None or pd is None:
        return _empty("revenue net income chart", frame, "plotly or pandas is not installed")
    y_cols = _numeric_columns(frame, ["revenue", "total_revenue", "net_income"])
    if not y_cols:
        return _empty("revenue net income chart", frame, "Revenue/net income fields are unavailable.")
    fig = px.bar(frame, x="period", y=y_cols, barmode="group")
    return _finish(fig, "Revenue / Net Income"), frame, ok_result(frame, source="reported income statement", provider="financial_charts", coverage=f"{len(y_cols)} fields")


def eps_reported_estimate_chart(earnings: Any = None):
    frame = _plot_frame(earnings)
    if px is None or pd is None:
        return _empty("eps reported estimate chart", frame, "plotly or pandas is not installed")
    y_cols = _numeric_columns(frame, ["eps_actual", "eps_estimate", "reported_eps", "estimated_eps"])
    if not y_cols or len(y_cols) < 2:
        return _empty("eps reported estimate chart", frame, "Reported and estimate EPS fields are unavailable.")
    fig = px.line(frame, x="period", y=y_cols, markers=True)
    return _finish(fig, "EPS Reported vs Estimate"), frame, ok_result(frame, source="earnings history", provider="financial_charts", coverage=f"{len(y_cols)} fields")


def revenue_reported_estimate_chart(revenue_estimates: Any = None):
    frame = _plot_frame(revenue_estimates)
    if px is None or pd is None:
        return _empty("revenue reported estimate chart", frame, "plotly or pandas is not installed")
    y_cols = _numeric_columns(frame, ["revenue_actual", "revenue_estimate", "reported_revenue", "estimated_revenue"])
    if not y_cols or len(y_cols) < 2:
        return _empty("revenue reported estimate chart", frame, "Reported and estimate revenue fields are unavailable.")
    fig = px.line(frame, x="period", y=y_cols, markers=True)
    return _finish(fig, "Revenue Reported vs Estimate"), frame, ok_result(frame, source="earnings revenue history", provider="financial_charts", coverage=f"{len(y_cols)} fields")


def margin_trend_chart(margins: Any = None):
    frame = _plot_frame(margins)
    if px is None or pd is None:
        return _empty("margin trend chart", frame, "plotly or pandas is not installed")
    y_cols = _numeric_columns(frame, ["gross_margin", "operating_margin", "net_margin", "ebitda_margin", "fcf_margin"])
    if not y_cols:
        return _empty("margin trend chart", frame, "Margin fields are unavailable.")
    fig = px.line(frame, x="period", y=y_cols, markers=True)
    return _finish(fig, "Margin Trends"), frame, ok_result(frame, source="reported statements", provider="financial_charts", coverage=f"{len(y_cols)} margin fields")


def valuation_ratio_chart(ratios: Any = None):
    frame = _plot_frame(ratios)
    if px is None or pd is None:
        return _empty("valuation ratio chart", frame, "plotly or pandas is not installed")
    if len(frame) == 1 and "period" in frame.columns:
        metric_rows = [{"metric": col, "value": frame.iloc[0][col]} for col in frame.columns if col != "period" and pd.notna(frame.iloc[0][col])]
        frame = pd.DataFrame(metric_rows)
        if frame.empty:
            return _empty("valuation ratio chart", frame, "Valuation ratio fields are unavailable.")
        fig = px.bar(frame, x="metric", y="value")
    else:
        y_cols = _numeric_columns(frame, ["trailing_pe", "forward_pe", "price_to_sales", "price_to_book", "ev_to_ebitda"])
        if not y_cols:
            return _empty("valuation ratio chart", frame, "Valuation ratio fields are unavailable.")
        fig = px.line(frame, x="period", y=y_cols, markers=True)
    return _finish(fig, "Valuation Ratios"), frame, ok_result(frame, source="valuation ratios", provider="financial_charts", coverage=f"{len(frame)} rows")


def profitability_ratio_chart(ratios: Any = None):
    frame = _plot_frame(ratios)
    if px is None or pd is None:
        return _empty("profitability ratio chart", frame, "plotly or pandas is not installed")
    if len(frame) == 1:
        metric_rows = [{"metric": col, "value": frame.iloc[0][col]} for col in ["roe", "roa", "roic", "gross_margin", "operating_margin", "net_margin", "fcf_margin"] if col in frame.columns and pd.notna(frame.iloc[0][col])]
        frame = pd.DataFrame(metric_rows)
        if frame.empty:
            return _empty("profitability ratio chart", frame, "Profitability ratio fields are unavailable.")
        fig = px.bar(frame, x="metric", y="value")
    else:
        y_cols = _numeric_columns(frame, ["roe", "roa", "roic", "gross_margin", "operating_margin", "net_margin", "fcf_margin"])
        if not y_cols:
            return _empty("profitability ratio chart", frame, "Profitability ratio fields are unavailable.")
        fig = px.line(frame, x="period", y=y_cols, markers=True)
    return _finish(fig, "Profitability Ratios"), frame, ok_result(frame, source="profitability ratios", provider="financial_charts", coverage=f"{len(frame)} rows")


def cashflow_chart(cashflow: Any = None):
    frame = _plot_frame(cashflow)
    if px is None or pd is None:
        return _empty("cashflow chart", frame, "plotly or pandas is not installed")
    y_cols = _numeric_columns(frame, ["operating_cash_flow", "capital_expenditure", "capex", "free_cash_flow", "financing_cash_flow", "investing_cash_flow"])
    if not y_cols:
        return _empty("cashflow chart", frame, "Cash flow fields are unavailable.")
    fig = px.bar(frame, x="period", y=y_cols, barmode="group")
    return _finish(fig, "Cash Flow"), frame, ok_result(frame, source="reported cash flow", provider="financial_charts", coverage=f"{len(y_cols)} fields")


def debt_cash_chart(balance: Any = None):
    frame = _plot_frame(balance)
    if px is None or pd is None:
        return _empty("debt cash chart", frame, "plotly or pandas is not installed")
    y_cols = _numeric_columns(frame, ["cash_and_equivalents", "total_debt", "net_debt"])
    if not y_cols:
        return _empty("debt cash chart", frame, "Debt/cash fields are unavailable.")
    fig = px.bar(frame, x="period", y=y_cols, barmode="group")
    return _finish(fig, "Debt / Cash"), frame, ok_result(frame, source="reported balance sheet", provider="financial_charts", coverage=f"{len(y_cols)} fields")


def balance_sheet_stack_chart(balance: Any = None):
    frame = _plot_frame(balance)
    if px is None or pd is None:
        return _empty("balance sheet stack chart", frame, "plotly or pandas is not installed")
    y_cols = _numeric_columns(frame, ["total_assets", "total_liabilities", "shareholders_equity", "current_assets", "current_liabilities"])
    if not y_cols:
        return _empty("balance sheet stack chart", frame, "Balance sheet fields are unavailable.")
    fig = px.bar(frame, x="period", y=y_cols, barmode="relative")
    return _finish(fig, "Balance Sheet Stack"), frame, ok_result(frame, source="reported balance sheet", provider="financial_charts", coverage=f"{len(y_cols)} fields")


def income_statement_stack_chart(income: Any = None):
    frame = _plot_frame(income)
    if px is None or pd is None:
        return _empty("income statement stack chart", frame, "plotly or pandas is not installed")
    y_cols = _numeric_columns(frame, ["total_revenue", "cost_of_revenue", "gross_profit", "operating_expense", "operating_income", "net_income"])
    if not y_cols:
        return _empty("income statement stack chart", frame, "Income statement fields are unavailable.")
    fig = px.bar(frame, x="period", y=y_cols, barmode="group")
    return _finish(fig, "Income Statement"), frame, ok_result(frame, source="reported income statement", provider="financial_charts", coverage=f"{len(y_cols)} fields")


def revenue_breakdown_chart(segments: Any = None):
    frame = _frame(segments)
    if px is None or pd is None:
        return _empty("revenue breakdown chart", frame, "plotly or pandas is not installed")
    if frame.empty or not {"segment", "revenue"}.issubset(frame.columns):
        return _empty("revenue breakdown chart", frame, "Real segment revenue data is unavailable.")
    fig = px.bar(frame, x="segment", y="revenue", color="segment")
    return _finish(fig, "Revenue By Segment"), frame, ok_result(frame, source="reported segment revenue", provider="financial_charts", coverage=f"{len(frame)} segments")


def geography_breakdown_chart(geography: Any = None):
    frame = _frame(geography)
    if px is None or pd is None:
        return _empty("geography breakdown chart", frame, "plotly or pandas is not installed")
    if frame.empty or not {"geography", "revenue"}.issubset(frame.columns):
        return _empty("geography breakdown chart", frame, "Real geographic revenue data is unavailable.")
    fig = px.bar(frame, x="geography", y="revenue", color="geography")
    return _finish(fig, "Revenue By Geography"), frame, ok_result(frame, source="reported geographic revenue", provider="financial_charts", coverage=f"{len(frame)} geographies")


def financial_waterfall_chart(income: Any = None):
    frame = _plot_frame(income)
    if go is None or pd is None:
        return _empty("financial waterfall chart", frame, "plotly or pandas is not installed")
    if frame.empty:
        return _empty("financial waterfall chart", frame, "Income statement fields are unavailable.")
    latest = frame.drop(columns=["period"], errors="ignore").dropna(how="all")
    if latest.empty:
        return _empty("financial waterfall chart", frame, "Income statement fields are unavailable.")
    row = latest.iloc[-1]
    labels = [label for label in ["total_revenue", "cost_of_revenue", "gross_profit", "operating_expense", "operating_income", "net_income"] if label in row.index and pd.notna(row[label])]
    if not labels:
        return _empty("financial waterfall chart", frame, "Income statement waterfall fields are unavailable.")
    values = [float(row[label]) for label in labels]
    fig = go.Figure(go.Waterfall(x=labels, y=values, measure=["relative"] * len(labels)))
    return _finish(fig, "Financial Waterfall"), frame, ok_result(frame, source="reported income statement", provider="financial_charts", coverage=f"{len(labels)} fields")


def data_availability_heatmap(availability: Any = None):
    frame = _frame(availability)
    if px is None or pd is None:
        return _empty("data availability heatmap", frame, "plotly or pandas is not installed")
    if frame.empty:
        return _empty("data availability heatmap", frame, "Availability rows are unavailable.")
    if "available" not in frame.columns:
        bool_cols = [col for col in frame.columns if col not in {"field", "provider", "source", "status"}]
        rows = [{"field": col, "available": bool(frame.iloc[0][col])} for col in bool_cols]
        frame = pd.DataFrame(rows)
    frame["availability_score"] = frame["available"].apply(lambda value: 1 if bool(value) else 0)
    fig = px.imshow([frame["availability_score"].tolist()], x=frame["field"] if "field" in frame.columns else frame.index, y=["available"], color_continuous_scale=["#334155", "#22c55e"], aspect="auto")
    return _finish(fig, "Data Availability"), frame, ok_result(frame, source="data availability matrix", provider="financial_charts", coverage=f"{len(frame)} fields")
