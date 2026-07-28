from __future__ import annotations
from typing import Any


def build_war_room_report_snapshot(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return {"snapshot_type": "war_room", "events": payload.get("events", []), "source_snapshot": payload.get("source_statuses", []), "freshness": payload.get("freshness", "unknown"), "confidence": payload.get("confidence", "unknown")}


def build_energy_report_snapshot(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return {"snapshot_type": "energy", "events": payload.get("events", []), "chokepoints": payload.get("chokepoints", []), "freshness": payload.get("freshness", "unknown"), "confidence": payload.get("confidence", "unknown")}


def build_provider_report_snapshot(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return {"snapshot_type": "provider", "providers": payload.get("providers", []), "gaps": payload.get("gaps", []), "freshness": payload.get("freshness", "unknown"), "confidence": payload.get("confidence", "unknown")}

