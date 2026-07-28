from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

from .cross_asset_regime_summary import summarize_cross_asset_regime
from .drilldown_recommendation_engine import build_drilldown_cards


RISK_STATES = ["calm", "watch", "elevated", "stressed", "critical", "data gap"]


def _risk_state(score: float | int | None, gaps: list[str] | None = None) -> str:
    if gaps and score is None:
        return "data gap"
    value = float(score if score is not None else 50)
    if value >= 90:
        return "critical"
    if value >= 75:
        return "stressed"
    if value >= 60:
        return "elevated"
    if value >= 35:
        return "watch"
    return "calm"


def build_what_changed_summary(payload: dict[str, Any] | None = None) -> list[str]:
    payload = payload or {}
    changes = payload.get("key_changes") or payload.get("changes") or []
    if changes:
        return [str(item) for item in changes][:6]
    return ["No material change list was supplied; inspect page-level charts for movement details."]


def build_cross_asset_risk_summary(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    regime = summarize_cross_asset_regime(payload or {})
    return {"state": regime["state"], "score": regime["score"], "drivers": regime["drivers"], "components": regime["components"]}


def build_data_confidence_summary(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    values = [float(value) for value in payload.get("source_confidence_values", []) if isinstance(value, (int, float))]
    confidence = round(mean(values), 1) if values else float(payload.get("source_confidence", 50))
    gaps = [str(item) for item in payload.get("data_gaps", [])]
    return {"score": confidence, "label": "gap" if gaps else "available", "missing_data": gaps, "caveat": "Confidence is based on supplied provider metadata."}


def build_proxy_vs_official_summary(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return {
        "official_outputs": [str(item) for item in payload.get("official_outputs", [])],
        "proxy_outputs": [str(item) for item in payload.get("proxy_outputs", payload.get("estimated_outputs", []))],
    }


def build_provider_health_summary(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    provider = (payload or {}).get("provider_health") or {}
    return {
        "ready_count": int(provider.get("ready_count", provider.get("available", 0) or 0)),
        "gap_count": int(provider.get("gap_count", provider.get("optional_missing", 0) or 0)),
        "status": provider.get("status", "available" if provider.get("available") else "unknown"),
    }


def build_next_drilldown_summary(payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return build_drilldown_cards(payload or {})


def build_alert_priority_stack(payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = payload or {}
    alerts = []
    for gap in payload.get("data_gaps", []):
        alerts.append({"priority": 80, "type": "data gap", "message": str(gap)})
    for driver in payload.get("risk_drivers", []):
        alerts.append({"priority": 70, "type": "risk driver", "message": str(driver)})
    if not alerts:
        alerts.append({"priority": 30, "type": "watch", "message": "No high-priority alert supplied."})
    return sorted(alerts, key=lambda item: item["priority"], reverse=True)


def build_global_executive_summary(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    data_confidence = build_data_confidence_summary(payload)
    cross_asset = build_cross_asset_risk_summary(payload.get("regime_payload", payload))
    score = payload.get("risk_score", cross_asset.get("score"))
    state = _risk_state(score, data_confidence["missing_data"])
    proxy_official = build_proxy_vs_official_summary(payload)
    return {
        "title": payload.get("title", "Global Executive Summary"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "global_risk_state": state,
        "key_changes": build_what_changed_summary(payload),
        "affected_assets": [str(item) for item in payload.get("affected_assets", [])],
        "cross_asset_channels": payload.get("cross_asset_channels", cross_asset.get("drivers", [])),
        "risk_drivers": payload.get("risk_drivers", cross_asset.get("drivers", [])),
        "data_confidence": data_confidence,
        "provider_health": build_provider_health_summary(payload),
        "proxy_outputs": proxy_official["proxy_outputs"],
        "official_outputs": proxy_official["official_outputs"],
        "missing_data": data_confidence["missing_data"],
        "next_drilldowns": build_next_drilldown_summary({**payload, "risk_state": state}),
        "alert_priority_stack": build_alert_priority_stack(payload),
        "caveats": payload.get("caveats", ["Research-only summary. Verify source status before relying on outputs."]),
    }


def build_workspace_executive_summary(workspace: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = build_global_executive_summary(payload)
    summary["title"] = f"{workspace} Executive Summary"
    summary["workspace"] = workspace
    return summary


def build_user_friendly_briefing(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = build_global_executive_summary(payload)
    summary["briefing"] = [
        f"Risk state: {summary['global_risk_state']}.",
        f"Data confidence: {summary['data_confidence']['score']}.",
        f"Provider gaps: {summary['provider_health']['gap_count']}.",
    ]
    return summary
