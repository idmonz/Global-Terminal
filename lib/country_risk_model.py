from __future__ import annotations

from statistics import mean
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    import plotly.express as px
except Exception:  # pragma: no cover
    px = None

from .data_status import error_result, ok_result


COUNTRY_METADATA = {
    "United States": {"iso2": "US", "iso3": "USA", "region": "Americas"},
    "China": {"iso2": "CN", "iso3": "CHN", "region": "Asia"},
    "Taiwan": {"iso2": "TW", "iso3": "TWN", "region": "Asia"},
    "South Korea": {"iso2": "KR", "iso3": "KOR", "region": "Korea"},
    "Japan": {"iso2": "JP", "iso3": "JPN", "region": "Asia"},
    "Iran": {"iso2": "IR", "iso3": "IRN", "region": "Middle East"},
    "Saudi Arabia": {"iso2": "SA", "iso3": "SAU", "region": "Middle East"},
    "Israel": {"iso2": "IL", "iso3": "ISR", "region": "Middle East"},
    "Egypt": {"iso2": "EG", "iso3": "EGY", "region": "Red Sea"},
    "Ukraine": {"iso2": "UA", "iso3": "UKR", "region": "Russia / Ukraine"},
    "Russia": {"iso2": "RU", "iso3": "RUS", "region": "Russia / Ukraine"},
    "Germany": {"iso2": "DE", "iso3": "DEU", "region": "Europe"},
    "Turkey": {"iso2": "TR", "iso3": "TUR", "region": "Europe"},
    "Panama": {"iso2": "PA", "iso3": "PAN", "region": "Americas"},
}

REGION_TO_COUNTRY = {
    "Americas": "United States",
    "Asia": "China",
    "Korea": "South Korea",
    "Middle East": "Iran",
    "Red Sea": "Egypt",
    "Russia / Ukraine": "Ukraine",
    "Europe": "Germany",
    "Global": "United States",
}

COMPONENT_WEIGHTS = {
    "unrest_score": 0.15,
    "conflict_score": 0.2,
    "security_score": 0.16,
    "information_score": 0.11,
    "market_stress_score": 0.15,
    "energy_chokepoint_score": 0.13,
    "source_freshness_penalty": 0.05,
    "data_gap_penalty": 0.05,
}

KEYWORDS = {
    "unrest_score": ["protest", "strike", "riot", "unrest", "demonstration"],
    "conflict_score": ["war", "missile", "attack", "invasion", "border", "military", "conflict"],
    "security_score": ["cyber", "terror", "sabotage", "explosion", "security", "drone"],
    "information_score": ["outage", "internet", "censorship", "misinformation", "media"],
    "energy_chokepoint_score": ["hormuz", "suez", "bab el-mandeb", "malacca", "panama canal", "bosphorus", "tanker", "chokepoint"],
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


def _clip(value: Any, low: float = 0.0, high: float = 100.0) -> float:
    try:
        number = float(value)
    except Exception:
        number = 0.0
    return max(low, min(high, number))


def _risk_level(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 45:
        return "elevated"
    if score >= 20:
        return "watch"
    return "low"


def _country_for_event(event: dict[str, Any]) -> str:
    country = str(event.get("country") or "").strip()
    if country:
        aliases = {"Korea": "South Korea", "US": "United States", "USA": "United States"}
        return aliases.get(country, country)
    return REGION_TO_COUNTRY.get(str(event.get("region") or "Global"), "United States")


def _component_from_events(events: list[dict[str, Any]], component: str) -> float:
    keywords = KEYWORDS.get(component, [])
    if not keywords:
        return 0.0
    score = 0.0
    for event in events:
        text = f"{event.get('title', '')} {event.get('summary', '')} {event.get('domain', '')}".lower()
        if any(keyword in text for keyword in keywords):
            score += {"critical": 30, "high": 22, "elevated": 15, "watch": 8, "low": 3}.get(str(event.get("severity") or "watch").lower(), 8)
    return _clip(score)


def compute_country_instability_score(
    country: str,
    events: Any = None,
    market_stress_score: Any = 0,
    source_freshness_penalty: Any = 0,
    data_gap_penalty: Any = 0,
) -> dict[str, Any]:
    rows = [event for event in _records(events) if _country_for_event(event).lower() == str(country or "").lower()]
    components = {
        "unrest_score": _component_from_events(rows, "unrest_score"),
        "conflict_score": _component_from_events(rows, "conflict_score"),
        "security_score": _component_from_events(rows, "security_score"),
        "information_score": _component_from_events(rows, "information_score"),
        "market_stress_score": _clip(market_stress_score),
        "energy_chokepoint_score": _component_from_events(rows, "energy_chokepoint_score"),
        "source_freshness_penalty": _clip(source_freshness_penalty),
        "data_gap_penalty": _clip(data_gap_penalty),
    }
    raw = sum(components[key] * weight for key, weight in COMPONENT_WEIGHTS.items())
    score = _clip(raw + min(18, len(rows) * 3))
    metadata = COUNTRY_METADATA.get(country, {"iso2": None, "iso3": None, "region": "Global"})
    drivers = [key.replace("_score", "").replace("_penalty", " penalty") for key, value in components.items() if value >= 20]
    gaps = []
    if not rows:
        gaps.append("No country-specific event rows available.")
    if components["source_freshness_penalty"] > 0:
        gaps.append("Some sources are stale, missing, or estimated.")
    if components["data_gap_penalty"] > 0:
        gaps.append("Data gaps affect this heuristic score.")
    return {
        "country": country,
        "iso2": metadata.get("iso2"),
        "iso3": metadata.get("iso3"),
        "region": metadata.get("region", "Global"),
        "instability_score": round(score, 1),
        "risk_level": _risk_level(score),
        "component_scores": components,
        "key_drivers": drivers or ["available event count"],
        "data_gaps": gaps,
        "caveat": "Heuristic regional/country risk score; not an official intelligence rating.",
    }


def compute_region_instability_score(region: str, events: Any = None) -> dict[str, Any]:
    rows = [event for event in _records(events) if str(event.get("region") or "Global").lower() == str(region or "Global").lower()]
    countries = sorted({_country_for_event(row) for row in rows}) or [REGION_TO_COUNTRY.get(region, "United States")]
    country_scores = [compute_country_instability_score(country, rows)["instability_score"] for country in countries]
    score = _clip(mean(country_scores) if country_scores else 0)
    return {
        "region": region or "Global",
        "instability_score": round(score, 1),
        "risk_level": _risk_level(score),
        "countries": countries,
        "event_count": len(rows),
        "caveat": "Heuristic regional aggregation of available event rows.",
    }


def build_country_risk_table(events: Any = None, market_stress: dict[str, Any] | None = None):
    rows = _records(events)
    countries = sorted({_country_for_event(event) for event in rows})
    if not countries:
        countries = ["United States", "China", "South Korea", "Iran", "Ukraine", "Germany"]
    output = []
    market_stress = market_stress or {}
    for country in countries:
        freshness_penalty = 10 if any(str(event.get("freshness_status") or event.get("freshness")).lower() in {"missing", "error", "stale"} for event in rows if _country_for_event(event) == country) else 0
        data_gap_penalty = 10 if any(event.get("data_gap") for event in rows if _country_for_event(event) == country) else 0
        payload = compute_country_instability_score(
            country,
            rows,
            market_stress_score=market_stress.get(country, 0),
            source_freshness_penalty=freshness_penalty,
            data_gap_penalty=data_gap_penalty,
        )
        output.append(
            {
                "country": payload["country"],
                "iso2": payload["iso2"],
                "iso3": payload["iso3"],
                "region": payload["region"],
                "instability_score": payload["instability_score"],
                "risk_level": payload["risk_level"],
                "component_scores": payload["component_scores"],
                "key_drivers": ", ".join(payload["key_drivers"]),
                "data_gaps": "; ".join(payload["data_gaps"]),
                "caveat": payload["caveat"],
            }
        )
    output = sorted(output, key=lambda item: item["instability_score"], reverse=True)
    return _frame(output)


def build_country_risk_cards(events: Any = None, limit: int = 8) -> list[dict[str, Any]]:
    table = build_country_risk_table(events)
    rows = table.head(limit).to_dict(orient="records") if hasattr(table, "head") else table[:limit]
    cards = []
    for row in rows:
        cards.append(
            {
                "title": f"{row['country']} heuristic risk",
                "summary": f"Score {row['instability_score']}/100 from available event, market, freshness, and data-gap components.",
                "severity": row["risk_level"],
                "freshness": "estimated",
                "source": "country_risk_model",
                "tags": [row["region"], "heuristic"],
                "bullets": [row.get("key_drivers") or "No key drivers", row.get("data_gaps") or "No explicit data gap", row["caveat"]],
            }
        )
    return cards


def build_country_risk_choropleth(events: Any = None):
    table = build_country_risk_table(events)
    if px is None or pd is None:
        return None, table, error_result(source="country risk choropleth", provider="plotly", error="plotly or pandas is not installed", is_estimated=True)
    if table.empty:
        return None, table, error_result(source="country risk choropleth", provider="country_risk_model", error="No country risk rows available", is_estimated=True)
    plot_frame = table.dropna(subset=["iso3"]).copy()
    if plot_frame.empty:
        return None, table, error_result(source="country risk choropleth", provider="country_risk_model", error="No ISO3 locations available", is_estimated=True)
    fig = px.choropleth(
        plot_frame,
        locations="iso3",
        color="instability_score",
        hover_name="country",
        hover_data=["region", "risk_level", "key_drivers", "data_gaps"],
        projection="natural earth",
        template="plotly_dark",
        color_continuous_scale="YlOrRd",
        range_color=[0, 100],
        title="Country Instability Heuristic",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=36, b=0))
    return fig, table, ok_result(table, source="country risk heuristic", provider="country_risk_model", is_estimated=True, coverage=f"{len(table)} countries")
