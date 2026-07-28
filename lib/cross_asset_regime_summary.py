from __future__ import annotations

from statistics import mean
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def _state(score: float) -> str:
    if score >= 80:
        return "stressed"
    if score >= 65:
        return "elevated"
    if score >= 45:
        return "watch"
    return "calm"


def _summary(name: str, score: float, drivers: list[str], source: str, quality: str = "proxy") -> dict[str, Any]:
    score = round(max(0.0, min(100.0, float(score))), 1)
    return {"regime": name, "state": _state(score), "score": score, "drivers": drivers, "source": source, "data_quality": quality, "caveat": "Regime summaries are heuristic and source-labeled."}


def summarize_equity_regime(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    score = float(payload.get("breadth_stress", payload.get("score", 50)))
    return _summary("equity", score, ["breadth", "trend"], payload.get("source", "price breadth"), payload.get("data_quality", "proxy"))


def summarize_rates_regime(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    score = float(payload.get("yield_stress", payload.get("score", 50)))
    return _summary("rates", score, ["yield curve", "real rates"], payload.get("source", "rates provider"), payload.get("data_quality", "proxy"))


def summarize_fx_regime(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    score = float(payload.get("dollar_stress", payload.get("score", 50)))
    return _summary("fx", score, ["dollar", "carry"], payload.get("source", "fx proxy"), payload.get("data_quality", "proxy"))


def summarize_crypto_regime(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    score = float(payload.get("derivatives_stress", payload.get("score", 50)))
    return _summary("crypto", score, ["funding", "open interest"], payload.get("source", "public crypto feeds"), payload.get("data_quality", "proxy"))


def summarize_energy_regime(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    score = float(payload.get("energy_risk", payload.get("score", 50)))
    return _summary("energy", score, ["oil", "chokepoints"], payload.get("source", "energy/chokepoint data"), payload.get("data_quality", "proxy"))


def summarize_geopolitical_regime(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    score = float(payload.get("instability_score", payload.get("score", 50)))
    return _summary("geopolitical", score, ["events", "country risk"], payload.get("source", "public OSINT/proxy"), payload.get("data_quality", "proxy"))


def summarize_cross_asset_regime(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    components = [
        summarize_equity_regime(payload.get("equity")),
        summarize_rates_regime(payload.get("rates")),
        summarize_fx_regime(payload.get("fx")),
        summarize_crypto_regime(payload.get("crypto")),
        summarize_energy_regime(payload.get("energy")),
        summarize_geopolitical_regime(payload.get("geopolitical")),
    ]
    score = round(mean(item["score"] for item in components), 1)
    return {"state": _state(score), "score": score, "components": components, "drivers": [item["regime"] for item in components if item["score"] >= 65], "source": "cross_asset_regime_summary", "data_quality": "mixed/proxy", "caveat": "Composite regime is heuristic research context."}


def build_cross_asset_regime_matrix(payload: dict[str, Any] | None = None):
    rows = summarize_cross_asset_regime(payload)["components"]
    return pd.DataFrame(rows) if pd is not None else rows
