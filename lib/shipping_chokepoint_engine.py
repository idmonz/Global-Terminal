from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


DEFAULT_CHOKEPOINTS = [
    {"chokepoint": "Strait of Hormuz", "region": "Middle East", "related_assets": ["CL=F", "BZ=F", "USO"], "base_score": 68},
    {"chokepoint": "Suez Canal", "region": "Egypt / Red Sea", "related_assets": ["shipping", "oil"], "base_score": 55},
    {"chokepoint": "Bab el-Mandeb", "region": "Red Sea", "related_assets": ["oil", "shipping"], "base_score": 62},
    {"chokepoint": "Panama Canal", "region": "Central America", "related_assets": ["shipping", "agriculture"], "base_score": 42},
    {"chokepoint": "Turkish Straits", "region": "Black Sea", "related_assets": ["wheat", "oil"], "base_score": 48},
]


def _severity_points(value: Any) -> float:
    lookup = {"critical": 25, "high": 18, "elevated": 12, "medium": 8, "watch": 4, "low": 0}
    return float(lookup.get(str(value).lower(), 0))


def compute_chokepoint_risk_score(chokepoint: dict[str, Any], *, related_news_severity: str | None = None, oil_price_move: float | None = None, provider_status: str | None = None, freshness: str | None = None) -> dict[str, Any]:
    score = float(chokepoint.get("base_score", 40))
    score += _severity_points(related_news_severity)
    if oil_price_move is not None:
        score += min(15.0, abs(float(oil_price_move)) * 2.0)
    if provider_status in {"missing", "error", "not configured"}:
        score += 4
    if freshness in {"stale", "estimated", "missing"}:
        score += 3
    score = round(max(0.0, min(100.0, score)), 1)
    return {
        "chokepoint": chokepoint.get("chokepoint") or chokepoint.get("name"),
        "region": chokepoint.get("region"),
        "risk_score": score,
        "related_assets": chokepoint.get("related_assets", []),
        "source": chokepoint.get("source", "static chokepoint registry"),
        "is_proxy": True,
        "caveat": "Chokepoint risk score is a proxy using static metadata, related news severity, oil moves, and source freshness.",
    }


def compute_route_exposure_score(route: dict[str, Any] | None = None, chokepoints: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    route = route or {}
    selected = chokepoints or DEFAULT_CHOKEPOINTS
    scores = [compute_chokepoint_risk_score(item)["risk_score"] for item in selected]
    return {
        "route": route.get("route") or "proxy route",
        "exposure_score": round(sum(scores) / max(1, len(scores)), 1),
        "chokepoint_count": len(selected),
        "is_proxy": True,
        "caveat": "Route exposure is proxy-based; no live AIS is used.",
    }


def compute_shipping_disruption_proxy(chokepoints: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    scores = [compute_chokepoint_risk_score(item)["risk_score"] for item in (chokepoints or DEFAULT_CHOKEPOINTS)]
    return {
        "shipping_disruption_proxy": round(max(scores) if scores else 0, 1),
        "average_chokepoint_risk": round(sum(scores) / max(1, len(scores)), 1),
        "is_proxy": True,
        "caveat": "No live vessel flow is claimed; this is a disruption proxy.",
    }


def build_chokepoint_risk_cards(chokepoints: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = [compute_chokepoint_risk_score(item) for item in (chokepoints or DEFAULT_CHOKEPOINTS)]
    return sorted(rows, key=lambda row: row["risk_score"], reverse=True)


def build_chokepoint_market_impact_payload(chokepoints: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    cards = build_chokepoint_risk_cards(chokepoints)
    return {
        "cards": cards,
        "top_related_assets": sorted({asset for card in cards for asset in card.get("related_assets", [])}),
        "market_channel": "potential energy, freight, inflation, and supply-chain channel",
        "is_proxy": True,
        "caveat": "Potential channel only; no causality is claimed.",
    }


def build_chokepoint_war_room_layer(chokepoints: list[dict[str, Any]] | None = None):
    rows = build_chokepoint_risk_cards(chokepoints)
    for row in rows:
        row["layer"] = "shipping_chokepoint_proxy"
        row["severity"] = "high" if row["risk_score"] >= 70 else "elevated" if row["risk_score"] >= 50 else "watch"
    return pd.DataFrame(rows) if pd is not None else rows
