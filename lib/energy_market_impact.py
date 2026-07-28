from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .shipping_chokepoint_engine import build_chokepoint_market_impact_payload


def _latest_move(data: Any) -> float | None:
    if pd is None or data is None or getattr(data, "empty", True):
        return None
    frame = data.copy()
    for col in ["daily_return", "return_1d_pct", "change_pct"]:
        if col in frame.columns:
            series = pd.to_numeric(frame[col], errors="coerce").dropna()
            if not series.empty:
                return float(series.iloc[-1])
    for col in ["close", "latest_price", "value"]:
        if col in frame.columns:
            series = pd.to_numeric(frame[col], errors="coerce").dropna()
            if len(series) >= 2:
                return float(series.pct_change().iloc[-1] * 100)
    return None


def compute_oil_market_impact(energy_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result = (energy_payload or {}).get("results", {}).get("commodity_spot")
    move = _latest_move(getattr(result, "data", None)) if result is not None else None
    score = 50.0 + max(-25.0, min(25.0, (move or 0.0) * 2.5))
    return {
        "impact_score": round(score, 1),
        "observed_related_move": move,
        "channel": "proxy oil price reaction",
        "is_proxy": True,
        "caveat": "Observed related move is not causality.",
    }


def compute_energy_equity_impact(energy_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    oil = compute_oil_market_impact(energy_payload)
    return {
        "energy_equity_score": round(min(100.0, max(0.0, oil["impact_score"] * 0.8 + 10)), 1),
        "related_assets": ["XLE", "USO", "CL=F", "BZ=F"],
        "channel": "potential energy equity sensitivity",
        "is_proxy": True,
        "caveat": "Sector sensitivity is proxy-based.",
    }


def compute_rates_energy_cross_impact(energy_payload: dict[str, Any] | None = None, macro_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    oil = compute_oil_market_impact(energy_payload)
    macro_confidence = float((macro_payload or {}).get("source_confidence", 0) or 0)
    return {
        "cross_impact_score": round((oil["impact_score"] + macro_confidence) / 2, 1),
        "channel": "potential inflation/rates transmission channel",
        "is_proxy": True,
        "caveat": "Rates-energy relationship is contextual evidence only.",
    }


def compute_chokepoint_oil_impact(chokepoints: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    payload = build_chokepoint_market_impact_payload(chokepoints)
    top_score = max([card["risk_score"] for card in payload["cards"]] or [0])
    return {
        "chokepoint_oil_score": top_score,
        "related_assets": payload["top_related_assets"],
        "channel": payload["market_channel"],
        "is_proxy": True,
        "caveat": payload["caveat"],
    }


def build_energy_market_impact_cards(energy_payload: dict[str, Any] | None = None, macro_payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    oil = compute_oil_market_impact(energy_payload)
    equity = compute_energy_equity_impact(energy_payload)
    rates = compute_rates_energy_cross_impact(energy_payload, macro_payload)
    choke = compute_chokepoint_oil_impact()
    return [
        {"label": "Oil Market Proxy", **oil},
        {"label": "Energy Equity Channel", **equity},
        {"label": "Rates / Energy Channel", **rates},
        {"label": "Chokepoint / Oil Channel", **choke},
    ]


def build_energy_scenario_evidence(energy_payload: dict[str, Any] | None = None, macro_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "energy_market_impact": build_energy_market_impact_cards(energy_payload, macro_payload),
        "scenario_language": ["proxy reaction", "potential channel", "observed related move"],
        "data_gaps": list((energy_payload or {}).get("data_gaps", [])) + list((macro_payload or {}).get("data_gaps", [])),
        "caveat": "Energy scenario evidence is informational and not a forecast guarantee.",
    }
