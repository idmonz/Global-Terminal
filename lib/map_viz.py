from __future__ import annotations

from typing import Any

from .data_status import failure, success

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


CHOKEPOINTS = [
    {"name": "Strait of Hormuz", "region": "Middle East", "lat": 26.5667, "lon": 56.25, "risk_proxy": "elevated", "source_status": "static chokepoint registry; AIS unavailable"},
    {"name": "Suez Canal", "region": "Egypt", "lat": 30.5852, "lon": 32.2654, "risk_proxy": "watch", "source_status": "static chokepoint registry; AIS unavailable"},
    {"name": "Bab el-Mandeb", "region": "Red Sea", "lat": 12.5833, "lon": 43.3333, "risk_proxy": "elevated", "source_status": "static chokepoint registry; AIS unavailable"},
    {"name": "Strait of Malacca", "region": "Southeast Asia", "lat": 2.5, "lon": 101.0, "risk_proxy": "watch", "source_status": "static chokepoint registry; AIS unavailable"},
    {"name": "Panama Canal", "region": "Panama", "lat": 9.08, "lon": -79.68, "risk_proxy": "watch", "source_status": "static chokepoint registry; AIS unavailable"},
    {"name": "Bosphorus", "region": "Turkey", "lat": 41.12, "lon": 29.07, "risk_proxy": "watch", "source_status": "static chokepoint registry; AIS unavailable"},
    {"name": "Dardanelles", "region": "Turkey", "lat": 40.15, "lon": 26.4, "risk_proxy": "watch", "source_status": "static chokepoint registry; AIS unavailable"},
    {"name": "Strait of Gibraltar", "region": "Western Mediterranean", "lat": 35.96, "lon": -5.55, "risk_proxy": "watch", "source_status": "static chokepoint registry; AIS unavailable"},
]


def _frame(rows):
    if pd is None:
        return rows
    return pd.DataFrame(rows)


def build_event_map(events=None):
    rows = []
    if events is not None:
        if hasattr(events, "to_dict"):
            rows = events.to_dict(orient="records")
        elif isinstance(events, list):
            rows = events
    rows = [row for row in rows if row.get("lat") is not None and row.get("lon") is not None]
    frame = _frame(rows)
    if px is None or pd is None:
        return None, frame, failure(source="event map", provider="plotly", error="plotly or pandas is not installed")
    if frame.empty:
        return None, frame, failure(source="event map", provider="map_viz", error="No events with coordinates available", coverage="fallback regional cards")
    fig = px.scatter_geo(frame, lat="lat", lon="lon", hover_name="title" if "title" in frame.columns else "name", color="severity" if "severity" in frame.columns else None, size="risk_score" if "risk_score" in frame.columns else None, projection="natural earth", template="plotly_dark")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    return fig, frame, success(frame, source="event map", provider="plotly", coverage=f"{len(frame)} mapped events")


def build_global_event_map(events=None):
    from .geo_layers import build_global_event_map as _build_global_event_map

    return _build_global_event_map(events)


def build_chokepoint_map(chokepoints=None):
    frame = _frame(chokepoints or CHOKEPOINTS)
    if px is None or pd is None:
        return None, frame, failure(source="chokepoint map", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    fig = px.scatter_geo(
        frame,
        lat="lat",
        lon="lon",
        hover_name="name",
        color="risk_proxy",
        hover_data=["region", "source_status"],
        projection="natural earth",
        template="plotly_dark",
    )
    fig.update_traces(marker=dict(size=10))
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), title="Energy Chokepoints - AIS unavailable without provider")
    return fig, frame, success(frame, source="static chokepoint registry", provider="map_viz", is_estimated=True, coverage=f"{len(frame)} chokepoints")


def build_country_risk_map(country_rows=None):
    rows = country_rows or [
        {"country": "United States", "risk_score": 35, "region": "North America"},
        {"country": "China", "risk_score": 55, "region": "Asia"},
        {"country": "South Korea", "risk_score": 45, "region": "Asia"},
        {"country": "Germany", "risk_score": 40, "region": "Europe"},
        {"country": "Saudi Arabia", "risk_score": 60, "region": "Middle East"},
    ]
    frame = _frame(rows)
    if px is None or pd is None:
        return None, frame, failure(source="country risk map", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    fig = px.choropleth(frame, locations="country", locationmode="country names", color="risk_score", hover_name="country", hover_data=["region"], projection="natural earth", template="plotly_dark", color_continuous_scale="YlOrRd")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    return fig, frame, success(frame, source="country risk proxy", provider="map_viz", is_estimated=True, coverage=f"{len(frame)} countries")


def build_energy_route_map_proxy(routes=None):
    routes = routes or [
        {"origin": "Persian Gulf", "destination": "Northeast Asia", "lat": [26.5, 12.6, 2.5, 35.7], "lon": [56.2, 43.3, 101.0, 139.7], "risk_proxy": "Hormuz / Bab el-Mandeb / Malacca route proxy"},
        {"origin": "US Gulf", "destination": "Europe", "lat": [29.7, 25.7, 35.9, 51.5], "lon": [-95.0, -80.2, -5.5, 0.0], "risk_proxy": "Atlantic route proxy"},
    ]
    if go is None:
        return None, routes, failure(source="energy route proxy", provider="plotly", error="plotly is not installed", is_estimated=True)
    fig = go.Figure()
    for route in routes:
        fig.add_trace(
            go.Scattergeo(
                lat=route["lat"],
                lon=route["lon"],
                mode="lines+markers",
                name=f"{route['origin']} to {route['destination']}",
                text=route["risk_proxy"],
            )
        )
    fig.update_layout(template="plotly_dark", geo=dict(projection_type="natural earth"), margin=dict(l=0, r=0, t=20, b=0), title="Energy Route Proxy - no live vessel flow")
    return fig, routes, success(routes, source="static route proxy", provider="map_viz", is_estimated=True, coverage=f"{len(routes)} route proxies", warning="No live vessel flow is claimed; AIS unavailable without provider.")


def build_market_region_map(region_rows=None):
    rows = region_rows or [
        {"region": "North America", "lat": 39.8, "lon": -98.6, "market_stress": 35, "label": "US / Canada"},
        {"region": "Europe", "lat": 50.1, "lon": 10.4, "market_stress": 40, "label": "Europe"},
        {"region": "Asia", "lat": 35.9, "lon": 104.2, "market_stress": 45, "label": "Asia"},
        {"region": "Middle East", "lat": 29.3, "lon": 47.7, "market_stress": 60, "label": "Energy risk region"},
    ]
    frame = _frame(rows)
    if px is None or pd is None:
        return None, frame, failure(source="market region map", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    fig = px.scatter_geo(frame, lat="lat", lon="lon", color="market_stress", size="market_stress", hover_name="label", projection="natural earth", template="plotly_dark", color_continuous_scale="OrRd")
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    return fig, frame, success(frame, source="market region stress proxy", provider="map_viz", is_estimated=True, coverage=f"{len(frame)} regions")


def _records(rows):
    if rows is None:
        return []
    if hasattr(rows, "to_dict"):
        return rows.to_dict(orient="records")
    if isinstance(rows, list):
        return [dict(row) for row in rows if isinstance(row, dict)]
    if isinstance(rows, dict):
        return [rows]
    return []


def _severity_score(value: Any) -> int:
    normalized = str(value or "watch").lower()
    if normalized in {"critical", "extreme"}:
        return 95
    if normalized in {"high", "elevated"}:
        return 78
    if normalized in {"medium"}:
        return 55
    if normalized in {"low"}:
        return 20
    return 35


def build_terminal_event_map(events=None):
    rows = []
    for row in _records(events):
        if row.get("lat") is None or row.get("lon") is None:
            continue
        severity = row.get("severity") or row.get("risk_proxy") or "watch"
        rows.append(
            {
                **row,
                "severity": severity,
                "risk_score": row.get("risk_score", row.get("severity_score", _severity_score(severity))),
                "hover_label": row.get("title") or row.get("name") or row.get("location") or "Event",
            }
        )
    frame = _frame(rows)
    if px is None or pd is None:
        return None, frame, failure(source="terminal event map", provider="plotly", error="plotly or pandas is not installed")
    if frame.empty:
        return None, frame, success(
            frame,
            source="terminal event map",
            provider="map_viz",
            warning="No events with coordinates available; using regional card/table fallback.",
            is_estimated=True,
            coverage="0 mapped events; fallback regional cards",
        )
    hover_cols = [col for col in ["region", "location", "source", "freshness", "classification_method", "coordinate_method"] if col in frame.columns]
    fig = px.scatter_geo(
        frame,
        lat="lat",
        lon="lon",
        hover_name="hover_label",
        hover_data=hover_cols,
        color="severity",
        size="risk_score",
        size_max=22,
        projection="natural earth",
        template="plotly_dark",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=26, b=0), title="Terminal Event Map - coordinate-backed public/proxy events")
    warning = None
    if "coordinate_method" in frame.columns and frame["coordinate_method"].astype(str).str.contains("centroid", case=False, na=False).any():
        warning = "Some event coordinates are heuristic region centroids, not exact event locations."
    return fig, frame, success(frame, source="terminal event map", provider="plotly", is_estimated=True, coverage=f"{len(frame)} mapped events", warning=warning)


def build_chokepoint_risk_map(chokepoints=None, news_items=None):
    news_records = _records(news_items)
    rows = []
    for item in chokepoints or CHOKEPOINTS:
        name = item["name"]
        related = 0
        for news in news_records:
            text = f"{news.get('title', '')} {news.get('summary', '')} {news.get('description', '')}".lower()
            tokens = [part for part in name.lower().replace("strait of ", "").replace("canal", "").split() if len(part) > 2]
            if any(token in text for token in tokens):
                related += 1
        risk_score = _severity_score(item.get("risk_proxy")) + related * 8
        rows.append({**item, "related_headlines": related, "risk_score": min(100, risk_score)})
    frame = _frame(rows)
    if px is None or pd is None:
        return None, frame, failure(source="chokepoint risk map", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    fig = px.scatter_geo(
        frame,
        lat="lat",
        lon="lon",
        hover_name="name",
        color="risk_score",
        size="risk_score",
        hover_data=["region", "risk_proxy", "related_headlines", "source_status"],
        projection="natural earth",
        template="plotly_dark",
        color_continuous_scale="YlOrRd",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=28, b=0), title="Chokepoint Risk Proxy - static registry, no live AIS claim")
    return fig, frame, success(frame, source="static chokepoint registry", provider="map_viz", is_estimated=True, coverage=f"{len(frame)} chokepoints", warning="No live AIS or vessel tracking is claimed.")


def build_market_region_risk_map(region_rows=None):
    return build_market_region_map(region_rows)


def build_energy_route_proxy_map(routes=None):
    return build_energy_route_map_proxy(routes)


def build_country_news_density_map(news_items=None):
    region_country = {
        "Middle East": "Saudi Arabia",
        "Red Sea": "Egypt",
        "Europe": "Germany",
        "Russia / Ukraine": "Ukraine",
        "Asia": "China",
        "Americas": "United States",
        "Global": "United States",
    }
    counts: dict[str, dict[str, Any]] = {}
    for row in _records(news_items):
        country = row.get("country") or region_country.get(str(row.get("region") or "Global"), "United States")
        payload = counts.setdefault(country, {"country": country, "headline_count": 0, "max_severity_score": 0, "region": row.get("region", "Global")})
        payload["headline_count"] += 1
        payload["max_severity_score"] = max(payload["max_severity_score"], _severity_score(row.get("severity")))
    frame = _frame(list(counts.values()))
    if px is None or pd is None:
        return None, frame, failure(source="country news density", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    if frame.empty:
        return None, frame, failure(source="country news density", provider="map_viz", error="No country or region-classified news available", coverage="fallback regional cards", is_estimated=True)
    frame["density_score"] = (frame["headline_count"] * 12 + frame["max_severity_score"]).clip(upper=100)
    fig = px.choropleth(
        frame,
        locations="country",
        locationmode="country names",
        color="density_score",
        hover_name="country",
        hover_data=["region", "headline_count", "max_severity_score"],
        projection="natural earth",
        template="plotly_dark",
        color_continuous_scale="YlOrRd",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=28, b=0), title="Country News Density - heuristic region mapping")
    return fig, frame, success(frame, source="public news density proxy", provider="map_viz", is_estimated=True, coverage=f"{len(frame)} countries")


def build_event_timeline_chart(timeline=None):
    frame = _frame(_records(timeline))
    if px is None or pd is None:
        return None, frame, failure(source="event timeline chart", provider="plotly", error="plotly or pandas is not installed")
    if frame.empty:
        return None, frame, failure(source="event timeline chart", provider="map_viz", error="No timeline rows available")
    if "period" not in frame.columns:
        time_col = next((col for col in ["published_at", "timeline_time", "date"] if col in frame.columns), None)
        if time_col:
            frame["period"] = pd.to_datetime(frame[time_col], utc=True, errors="coerce").dt.floor("D")
            frame = frame.dropna(subset=["period"]).groupby("period").size().reset_index(name="total_count")
    y_col = "total_count" if "total_count" in frame.columns else frame.columns[-1]
    if "period" not in frame.columns:
        return None, frame, failure(source="event timeline chart", provider="map_viz", error="Timeline period column unavailable")
    fig = px.bar(frame, x="period", y=y_col, template="plotly_dark", title="Event Timeline")
    for col, color in [("critical_count", "#ef4444"), ("high_count", "#f97316"), ("medium_count", "#f59e0b")]:
        if col in frame.columns and go is not None:
            fig.add_trace(go.Scatter(x=frame["period"], y=frame[col], mode="lines+markers", name=col.replace("_", " "), line=dict(color=color)))
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=26))
    return fig, frame, success(frame, source="event timeline chart", provider="plotly", coverage=f"{len(frame)} periods")


def build_news_severity_bar(items=None):
    rows = _records(items)
    counts: dict[str, int] = {}
    for row in rows:
        severity = str(row.get("severity") or "watch").lower()
        counts[severity] = counts.get(severity, 0) + 1
    frame = _frame([{"severity": key, "count": value, "severity_score": _severity_score(key)} for key, value in counts.items()])
    if px is None or pd is None:
        return None, frame, failure(source="news severity bar", provider="plotly", error="plotly or pandas is not installed")
    if frame.empty:
        return None, frame, failure(source="news severity bar", provider="map_viz", error="No severity-classified news rows available")
    fig = px.bar(frame.sort_values("severity_score", ascending=False), x="severity", y="count", color="severity", template="plotly_dark", title="News Severity Mix")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=26))
    return fig, frame, success(frame, source="news severity bar", provider="plotly", is_estimated=True, coverage=f"{len(frame)} severity buckets")


def build_source_freshness_chart(statuses=None):
    from .source_freshness import source_freshness_table

    if pd is not None and hasattr(statuses, "columns") and {"source", "status"}.issubset(statuses.columns):
        frame = statuses.copy()
    else:
        frame = source_freshness_table(statuses or [])
    if px is None or pd is None:
        return None, frame, failure(source="source freshness chart", provider="plotly", error="plotly or pandas is not installed")
    if frame.empty:
        return None, frame, failure(source="source freshness chart", provider="map_viz", error="No source freshness rows available")
    counts = frame.groupby("status").size().reset_index(name="source_count")
    fig = px.bar(counts, x="status", y="source_count", color="status", template="plotly_dark", title="Source Freshness")
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=26))
    return fig, frame, success(frame, source="source freshness chart", provider="plotly", coverage=f"{len(frame)} sources")
