from __future__ import annotations

from typing import Any

from .data_status import error_result, ok_result
from .event_stream import CHOKEPOINTS, build_event_stream

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


SEVERITY_COLORS = {
    "critical": "#ef4444",
    "high": "#f97316",
    "elevated": "#f59e0b",
    "watch": "#38bdf8",
    "low": "#22c55e",
}


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


def _frame(rows: list[dict[str, Any]]):
    return pd.DataFrame(rows) if pd is not None else rows


def _empty_status(name: str, frame=None, message: str = "No rows available"):
    return None, frame if frame is not None else _frame([]), error_result(source=name, provider="geo_layers", error=message, is_estimated=True)


def _style_geo(fig):
    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor="#0f172a",
        showocean=True,
        oceancolor="#020617",
        showcountries=True,
        countrycolor="rgba(148,163,184,0.35)",
        coastlinecolor="rgba(148,163,184,0.35)",
        bgcolor="#020617",
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#020617",
        plot_bgcolor="#020617",
        margin=dict(l=0, r=0, t=36, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01),
    )
    return fig


def build_global_event_map(events: Any = None):
    rows = [row for row in _records(events) if row.get("lat") is not None and row.get("lon") is not None]
    frame = _frame(rows)
    if px is None or pd is None:
        return None, frame, error_result(source="global event map", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    if frame.empty:
        return _empty_status("global event map", frame, "No coordinate-backed or approximate centroid events available")
    if "severity_score" not in frame.columns:
        score_map = {"critical": 95, "high": 78, "elevated": 55, "watch": 30, "low": 15}
        frame["severity_score"] = frame["severity"].map(score_map).fillna(30)
    hover_cols = [col for col in ["summary", "domain", "region", "country", "source", "provider", "freshness_status", "credibility", "data_gap", "approximate_location"] if col in frame.columns]
    fig = px.scatter_geo(
        frame,
        lat="lat",
        lon="lon",
        color="severity",
        size="severity_score",
        size_max=26,
        hover_name="title",
        hover_data=hover_cols,
        color_discrete_map=SEVERITY_COLORS,
        title="Global Event Map - source-backed or approximate centroid events",
    )
    _style_geo(fig)
    return fig, frame, ok_result(frame, source="global event map", provider="geo_layers", is_estimated=True, coverage=f"{len(frame)} mapped events")


def build_chokepoint_layer(chokepoints: Any = None):
    rows = _records(chokepoints) or CHOKEPOINTS
    frame = _frame(
        [
            {
                **row,
                "name": row.get("name") or row.get("title"),
                "risk_score": row.get("risk_score") or 45,
                "source_status": "static registry; no live AIS or vessel tracking",
            }
            for row in rows
        ]
    )
    if px is None or pd is None:
        return None, frame, error_result(source="chokepoint layer", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    fig = px.scatter_geo(
        frame,
        lat="lat",
        lon="lon",
        size="risk_score",
        color="risk_score",
        hover_name="name",
        hover_data=["region", "country", "source_status", "related_tickers"],
        color_continuous_scale="YlOrRd",
        range_color=[0, 100],
        title="Energy Chokepoints - static registry / route exposure proxy",
    )
    _style_geo(fig)
    return fig, frame, ok_result(frame, source="static chokepoint registry", provider="geo_layers", is_estimated=True, coverage=f"{len(frame)} chokepoints", warning="No live AIS or vessel flow is claimed.")


def build_country_instability_layer(country_rows: Any = None):
    from .country_risk_model import build_country_risk_table

    table = country_rows if hasattr(country_rows, "columns") else build_country_risk_table(country_rows)
    if px is None or pd is None:
        return None, table, error_result(source="country instability layer", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    if table is None or table.empty or "iso3" not in table.columns:
        return _empty_status("country instability layer", table, "No country ISO3 rows available")
    plot_frame = table.dropna(subset=["iso3"]).copy()
    if plot_frame.empty:
        return _empty_status("country instability layer", table, "No country ISO3 rows available")
    fig = px.choropleth(
        plot_frame,
        locations="iso3",
        color="instability_score",
        hover_name="country",
        hover_data=["region", "risk_level", "key_drivers", "data_gaps"],
        color_continuous_scale="YlOrRd",
        range_color=[0, 100],
        title="Country Instability Heuristic - not official",
    )
    _style_geo(fig)
    return fig, table, ok_result(table, source="country instability heuristic", provider="geo_layers", is_estimated=True, coverage=f"{len(table)} countries")


def build_energy_route_proxy_layer(routes: Any = None):
    routes = _records(routes) or [
        {"origin": "Persian Gulf", "destination": "Northeast Asia", "lat": [26.5, 12.6, 2.5, 35.7], "lon": [56.2, 43.3, 101.0, 139.7], "risk_proxy": "Hormuz / Bab el-Mandeb / Malacca route exposure proxy"},
        {"origin": "US Gulf", "destination": "Europe", "lat": [29.7, 25.7, 35.9, 51.5], "lon": [-95.0, -80.2, -5.5, 0.0], "risk_proxy": "Atlantic route exposure proxy"},
        {"origin": "Black Sea", "destination": "Mediterranean", "lat": [44.6, 41.1, 40.1, 35.9], "lon": [33.5, 29.1, 26.4, -5.5], "risk_proxy": "Black Sea / Turkish Straits exposure proxy"},
    ]
    if go is None:
        return None, routes, error_result(source="energy route proxy layer", provider="plotly", error="plotly is not installed", is_estimated=True)
    fig = go.Figure()
    for route in routes:
        fig.add_trace(
            go.Scattergeo(
                lat=route["lat"],
                lon=route["lon"],
                mode="lines+markers",
                line=dict(width=2, color="#f59e0b"),
                marker=dict(size=5),
                name=f"{route['origin']} to {route['destination']}",
                text=route["risk_proxy"],
                hovertemplate="%{text}<extra></extra>",
            )
        )
    fig.update_layout(title="Route Exposure Proxy - no live vessel traffic")
    _style_geo(fig)
    return fig, routes, ok_result(routes, source="static route exposure proxy", provider="geo_layers", is_estimated=True, coverage=f"{len(routes)} routes", warning="Route arcs are exposure proxies, no live vessel traffic.")


def build_crypto_market_stress_layer(crypto_rows: Any = None):
    rows = _records(crypto_rows) or [
        {"region": "Global Crypto", "lat": 20.0, "lon": 0.0, "stress_score": 0, "summary": "Crypto stress data gap unless derivatives context is supplied.", "source": "data gap"},
    ]
    frame = _frame(rows)
    if px is None or pd is None:
        return None, frame, error_result(source="crypto market stress layer", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    fig = px.scatter_geo(
        frame,
        lat="lat",
        lon="lon",
        size="stress_score",
        color="stress_score",
        hover_name="region",
        hover_data=[col for col in ["summary", "source"] if col in frame.columns],
        color_continuous_scale="Bluered",
        range_color=[0, 100],
        title="Crypto Market Stress Proxy",
    )
    _style_geo(fig)
    return fig, frame, ok_result(frame, source="crypto stress proxy", provider="geo_layers", is_estimated=True, coverage=f"{len(frame)} stress nodes")


def build_market_region_layer(region_rows: Any = None):
    rows = _records(region_rows) or [
        {"region": "Americas", "label": "US / Americas", "lat": 39.8, "lon": -98.6, "market_stress": 0, "source": "data gap"},
        {"region": "Europe", "label": "Europe", "lat": 50.1, "lon": 10.4, "market_stress": 0, "source": "data gap"},
        {"region": "Asia", "label": "Asia", "lat": 35.9, "lon": 104.2, "market_stress": 0, "source": "data gap"},
        {"region": "Middle East", "label": "Middle East", "lat": 29.3, "lon": 47.7, "market_stress": 0, "source": "data gap"},
    ]
    frame = _frame(rows)
    if px is None or pd is None:
        return None, frame, error_result(source="market region layer", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    fig = px.scatter_geo(
        frame,
        lat="lat",
        lon="lon",
        size="market_stress",
        color="market_stress",
        hover_name="label",
        hover_data=["region", "source"],
        color_continuous_scale="OrRd",
        range_color=[0, 100],
        title="Regional Market Stress Proxy",
    )
    _style_geo(fig)
    return fig, frame, ok_result(frame, source="regional market stress proxy", provider="geo_layers", is_estimated=True, coverage=f"{len(frame)} regions")


def build_event_density_layer(events: Any = None):
    rows = [row for row in _records(events) if row.get("lat") is not None and row.get("lon") is not None]
    frame = _frame(rows)
    if px is None or pd is None:
        return None, frame, error_result(source="event density layer", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    if frame.empty:
        return _empty_status("event density layer", frame, "No coordinate-backed events available")
    frame["density_weight"] = frame.get("severity_score", 30)
    fig = px.density_mapbox(
        frame,
        lat="lat",
        lon="lon",
        z="density_weight",
        radius=24,
        hover_name="title",
        mapbox_style="carto-darkmatter",
        zoom=0,
        center={"lat": 15, "lon": 15},
        title="Event Density Proxy",
    )
    fig.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=36, b=0))
    return fig, frame, ok_result(frame, source="event density proxy", provider="geo_layers", is_estimated=True, coverage=f"{len(frame)} density points")


def build_route_arc_layer(routes: Any = None):
    return build_energy_route_proxy_layer(routes)


def build_layered_event_map(events: Any = None, layers: list[str] | None = None):
    event_rows = build_event_stream(news=events) if not events or not all("event_id" in row for row in _records(events)) else _records(events)
    fig, frame, status = build_global_event_map(event_rows)
    if fig is None or go is None:
        return fig, frame, status
    selected = set(layers or ["events", "chokepoints", "routes"])
    if "chokepoints" in selected:
        for point in CHOKEPOINTS:
            fig.add_trace(
                go.Scattergeo(
                    lat=[point["lat"]],
                    lon=[point["lon"]],
                    mode="markers",
                    marker=dict(size=10, symbol="diamond", color="#f59e0b", line=dict(width=1, color="#fef3c7")),
                    name=point["title"],
                    text=f"{point['title']}<br>Static chokepoint registry<br>No live AIS",
                    hovertemplate="%{text}<extra></extra>",
                )
            )
    if "routes" in selected:
        route_fig, _, _ = build_energy_route_proxy_layer()
        if route_fig is not None:
            for trace in route_fig.data:
                fig.add_trace(trace)
    fig.update_layout(title="Layered War Room Map - events, static chokepoints, route proxies")
    return fig, frame, status
