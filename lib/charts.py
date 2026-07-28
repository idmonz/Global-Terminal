from __future__ import annotations

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


PLOTLY_TEMPLATE = "plotly_dark"


def normalize_price_history_columns(data, ticker: str | None = None):
    """Flatten common yfinance single-ticker MultiIndex columns for Plotly."""
    if pd is None or data is None or getattr(data, "empty", True):
        return data
    frame = data.copy()
    if not isinstance(frame.columns, pd.MultiIndex):
        return frame
    ticker_key = (ticker or "").upper()
    if ticker_key:
        for level in range(frame.columns.nlevels):
            values = list(frame.columns.get_level_values(level))
            match = next((value for value in values if str(value).upper() == ticker_key), None)
            if match is not None:
                flattened = frame.xs(match, axis=1, level=level, drop_level=True).copy()
                if isinstance(flattened.columns, pd.MultiIndex):
                    flattened.columns = [
                        next((str(part) for part in column if str(part)), str(column))
                        for column in flattened.columns
                    ]
                return flattened
    flattened = frame.copy()
    for level in reversed(range(flattened.columns.nlevels)):
        values = [value for value in flattened.columns.get_level_values(level).unique() if str(value)]
        if len(values) == 1:
            flattened = flattened.droplevel(level, axis=1)
            if not isinstance(flattened.columns, pd.MultiIndex):
                break
    if isinstance(flattened.columns, pd.MultiIndex):
        flattened.columns = [
            " ".join(str(part) for part in column if str(part)).strip() or str(column)
            for column in flattened.columns
        ]
    return flattened


def _annotate(fig, *, source: str = "", fetched_at: str | None = None):
    note = source or "source unavailable"
    if fetched_at:
        note = f"{note} | Last updated: {fetched_at}"
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        margin=dict(l=12, r=12, t=48, b=36),
        annotations=[
            dict(
                text=note,
                x=0,
                y=-0.12,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=11, color="#9ca3af"),
                align="left",
            )
        ],
    )
    return fig


def make_line(data, *, x: str, y: str, title: str, source: str = "", fetched_at: str | None = None):
    if px is None:
        return None
    fig = px.line(data, x=x, y=y, title=title)
    return _annotate(fig, source=source, fetched_at=fetched_at)


def make_bar(data, *, x: str, y: str, color: str | None = None, title: str, source: str = "", fetched_at: str | None = None):
    if px is None:
        return None
    fig = px.bar(data, x=x, y=y, color=color, title=title)
    return _annotate(fig, source=source, fetched_at=fetched_at)


def make_heatmap(data, *, title: str, source: str = "", fetched_at: str | None = None):
    if px is None:
        return None
    fig = px.imshow(data, text_auto=True, title=title, color_continuous_scale="RdBu", aspect="auto")
    return _annotate(fig, source=source, fetched_at=fetched_at)


def make_treemap(
    data,
    *,
    title: str,
    label_col: str = "name",
    parent_col: str = "sector",
    value_col: str = "size_value",
    color_col: str = "daily_return",
    color_label: str | None = None,
    source: str = "",
    fetched_at: str | None = None,
):
    if px is None:
        return None
    frame = data.copy()
    if label_col not in frame.columns:
        frame[label_col] = frame.get("ticker", "Unknown")
    if parent_col not in frame.columns:
        frame[parent_col] = "Market"
    if value_col not in frame.columns:
        frame[value_col] = 1
    if color_col not in frame.columns:
        frame[color_col] = 0
    frame[value_col] = frame[value_col].fillna(1)
    frame["_color_value"] = frame[color_col].fillna(0)
    hover_cols = [col for col in ["ticker", "company", "sector", "industry", "price", "volume", "market_cap", "data_quality"] if col in frame.columns]
    fig = px.treemap(
        frame,
        path=[parent_col, label_col],
        values=value_col,
        color="_color_value",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        hover_data=hover_cols + ([color_col] if color_col in frame.columns else []),
        labels={"_color_value": color_label or color_col, color_col: color_label or color_col},
        title=title,
    )
    fig.update_traces(root_color="#111827")
    fig.update_coloraxes(colorbar_title_text=color_label or color_col)
    return _annotate(fig, source=source, fetched_at=fetched_at)
