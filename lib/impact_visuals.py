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


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return value.to_dict(orient="records")
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [dict(value)]
    return []


def _frame(value: Any):
    if pd is None:
        return value or []
    if value is None:
        return pd.DataFrame()
    if hasattr(value, "copy") and hasattr(value, "columns"):
        return value.copy()
    return pd.DataFrame(_records(value))


def _empty(name: str, frame=None, message: str = "Required data unavailable."):
    return None, frame if frame is not None else _frame(None), error_result(source=name, provider="impact_visuals", error=message, coverage="data gap")


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


def market_impact_matrix_chart(impact_rows: Any = None):
    frame = _frame(impact_rows)
    if px is None or pd is None:
        return _empty("market impact matrix chart", frame, "plotly or pandas is not installed")
    if frame.empty or not {"ticker", "event_title", "relevance_score"}.issubset(frame.columns):
        return _empty("market impact matrix chart", frame, "Impact matrix rows are unavailable.")
    pivot = frame.pivot_table(index="event_title", columns="ticker", values="relevance_score", aggfunc="max", fill_value=0)
    fig = px.imshow(pivot, color_continuous_scale="YlOrRd", aspect="auto")
    return _finish(fig, "News to Market Impact Matrix"), frame, ok_result(frame, source="impact matrix", provider="impact_visuals", coverage=f"{len(frame)} rows", is_estimated=True)


def event_asset_heatmap(impact_rows: Any = None):
    return market_impact_matrix_chart(impact_rows)


def catalyst_sankey_chart(graph: dict[str, Any] | None = None):
    if go is None or pd is None:
        return _empty("catalyst sankey chart", _frame(None), "plotly or pandas is not installed")
    graph = graph or {}
    nodes = _frame(graph.get("nodes"))
    edges = _frame(graph.get("edges"))
    if nodes.empty or edges.empty:
        return _empty("catalyst sankey chart", edges, "Catalyst graph nodes/edges are unavailable.")
    labels = nodes["node_id"].astype(str).tolist()
    label_index = {label: idx for idx, label in enumerate(labels)}
    valid = edges[edges["source"].astype(str).isin(label_index) & edges["target"].astype(str).isin(label_index)].copy()
    if valid.empty:
        return _empty("catalyst sankey chart", edges, "No valid source-target edges available.")
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(label=nodes["label"].astype(str).tolist(), pad=12, thickness=12, color="#334155"),
                link=dict(
                    source=[label_index[str(item)] for item in valid["source"]],
                    target=[label_index[str(item)] for item in valid["target"]],
                    value=[max(1, float(item or 1)) for item in valid["weight"]],
                    label=valid["edge_type"].astype(str).tolist(),
                    color="rgba(56,189,248,0.28)",
                ),
            )
        ]
    )
    return _finish(fig, "Catalyst Graph Sankey"), valid, ok_result(valid, source="catalyst graph", provider="impact_visuals", coverage=f"{len(valid)} edges", is_estimated=True)


def event_timeline_with_market_overlay(events: Any = None, impact_rows: Any = None):
    if px is None or go is None or pd is None:
        return _empty("event timeline market overlay", _frame(None), "plotly or pandas is not installed")
    event_frame = _frame(events)
    impact_frame = _frame(impact_rows)
    if event_frame.empty or "timestamp" not in event_frame.columns:
        return _empty("event timeline market overlay", event_frame, "Event timestamps are unavailable.")
    event_frame["period"] = pd.to_datetime(event_frame["timestamp"], utc=True, errors="coerce").dt.floor("D")
    counts = event_frame.dropna(subset=["period"]).groupby("period").size().reset_index(name="event_count")
    if counts.empty:
        return _empty("event timeline market overlay", event_frame, "No dated events available.")
    fig = px.bar(counts, x="period", y="event_count")
    if not impact_frame.empty and "return_1d_pct" in impact_frame.columns:
        overlay = impact_frame.copy()
        overlay["abs_move"] = pd.to_numeric(overlay["return_1d_pct"], errors="coerce").abs()
        if "event_id" in overlay.columns:
            event_lookup = event_frame.set_index(event_frame.get("event_id", event_frame["title"]))["period"].to_dict()
            overlay["period"] = overlay["event_id"].map(event_lookup)
        if "period" in overlay.columns:
            overlay = overlay.dropna(subset=["period"]).groupby("period")["abs_move"].mean().reset_index()
            fig.add_trace(go.Scatter(x=overlay["period"], y=overlay["abs_move"], name="avg abs 1D proxy move", mode="lines+markers", yaxis="y2"))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", title="avg abs 1D proxy move"))
    return _finish(fig, "Event Timeline With Market Overlay"), counts, ok_result(counts, source="event/impact timeline", provider="impact_visuals", coverage=f"{len(counts)} periods", is_estimated=True)


def asset_reaction_bar_chart(impact_rows: Any = None):
    frame = _frame(impact_rows)
    if px is None or pd is None:
        return _empty("asset reaction bar chart", frame, "plotly or pandas is not installed")
    if frame.empty or "ticker" not in frame.columns:
        return _empty("asset reaction bar chart", frame, "Asset reaction rows are unavailable.")
    metric = "return_1d_pct" if "return_1d_pct" in frame.columns and pd.to_numeric(frame["return_1d_pct"], errors="coerce").notna().any() else "relevance_score"
    if metric not in frame.columns:
        return _empty("asset reaction bar chart", frame, "No asset reaction or relevance values available.")
    plot_frame = frame.dropna(subset=[metric]).copy()
    if plot_frame.empty:
        return _empty("asset reaction bar chart", frame, "No asset reaction or relevance values available.")
    plot_frame = plot_frame.groupby("ticker")[metric].mean().reset_index().sort_values(metric, key=lambda series: series.abs(), ascending=False).head(20)
    fig = px.bar(plot_frame, x="ticker", y=metric, color=metric, color_continuous_scale="RdBu")
    title = "Asset Proxy Reaction" if metric == "return_1d_pct" else "Related Asset Relevance Proxy"
    warning = None if metric == "return_1d_pct" else "Price reactions unavailable; chart uses related-asset relevance scores."
    return _finish(fig, title), plot_frame, ok_result(plot_frame, source="asset reaction rows", provider="impact_visuals", coverage=f"{len(plot_frame)} assets", is_estimated=True, warning=warning)


def scenario_evidence_contribution_chart(evidence_rows: Any = None):
    frame = _frame(evidence_rows)
    if px is None or pd is None:
        return _empty("scenario evidence contribution chart", frame, "plotly or pandas is not installed")
    if frame.empty or "news_impact_evidence" not in frame.columns:
        return _empty("scenario evidence contribution chart", frame, "Scenario evidence rows are unavailable.")
    plot_frame = frame.copy()
    plot_frame["event_label"] = plot_frame.get("event_title", plot_frame.get("event_id", "")).astype(str).str.slice(0, 80)
    fig = px.bar(plot_frame, x="event_label", y="news_impact_evidence", color="news_impact_evidence", color_continuous_scale="YlOrRd")
    return _finish(fig, "Scenario Evidence Contribution"), plot_frame, ok_result(plot_frame, source="scenario evidence rows", provider="impact_visuals", coverage=f"{len(plot_frame)} rows", is_estimated=True)
