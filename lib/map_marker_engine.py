from __future__ import annotations

from typing import Any


def _marker(marker_type: str, item: dict[str, Any], *, label: str | None = None, severity: str = "watch", source: str | None = None, freshness: str = "estimated", confidence: float | int | None = None, command: str | None = None, caveat: str | None = None) -> dict[str, Any]:
    return {
        "marker_type": marker_type,
        "lat": item.get("lat"),
        "lon": item.get("lon"),
        "label": label or str(item.get("label") or item.get("title") or item.get("name") or marker_type),
        "severity": item.get("severity") or severity,
        "source": source or item.get("source") or "unknown",
        "freshness": item.get("freshness") or freshness,
        "confidence": item.get("confidence", confidence),
        "truth_label": item.get("truth_label") or item.get("source_type") or freshness,
        "click_action": {"command": command or item.get("command") or f"WAR ROOM {item.get('region', '')}".strip()},
        "caveat": caveat or item.get("caveat"),
    }


def build_event_marker(event: dict[str, Any]) -> dict[str, Any]:
    return _marker("event", event, command=f"WAR ROOM {event.get('region', 'Global')}")


def build_vessel_marker(vessel: dict[str, Any], *, provider_status: dict[str, Any] | None = None) -> dict[str, Any]:
    provider_status = provider_status or {}
    is_live = bool(provider_status.get("ok") and provider_status.get("live"))
    freshness = "live" if is_live else "historical-only" if str(vessel.get("source", "")).lower().startswith("noaa") else "unavailable"
    caveat = None if is_live else "No live vessel marker is claimed without a successful live AIS probe."
    return _marker("vessel", {**vessel, "freshness": freshness, "truth_label": freshness}, source=vessel.get("source", "AIS"), freshness=freshness, command="WAR ROOM AIS", caveat=caveat)


def build_port_marker(port: dict[str, Any]) -> dict[str, Any]:
    return _marker("port", port, freshness="estimated", command=f"WAR ROOM {port.get('name', 'port')}")


def build_chokepoint_marker(chokepoint: dict[str, Any]) -> dict[str, Any]:
    return _marker("chokepoint", chokepoint, severity=str(chokepoint.get("risk_level") or "watch"), source="static chokepoint registry", freshness="estimated", command=f"{chokepoint.get('name', 'CL')} ENERGY")


def build_weather_marker(weather: dict[str, Any]) -> dict[str, Any]:
    return _marker("weather", weather, source=weather.get("source", "Open-Meteo"), freshness=weather.get("freshness", "estimated"), command="WAR ROOM weather")


def build_earthquake_marker(event: dict[str, Any]) -> dict[str, Any]:
    return _marker("earthquake", event, source=event.get("source", "USGS"), freshness=event.get("freshness", "fresh"), command="WAR ROOM earthquakes")


def build_provider_gap_marker(gap: dict[str, Any]) -> dict[str, Any]:
    return _marker("provider_gap", {**gap, "lat": gap.get("lat", 20.0), "lon": gap.get("lon", 0.0), "truth_label": "missing-key"}, source=gap.get("provider", "provider probe"), freshness="missing-key", command="DATA PROBE", caveat="Provider gap marker is an operational diagnostic.")


def build_map_marker_payload(events: list[dict[str, Any]] | None = None, provider_gaps: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    markers = [build_event_marker(event) for event in events or [] if event.get("lat") is not None and event.get("lon") is not None]
    markers.extend(build_provider_gap_marker(gap) for gap in provider_gaps or [])
    return {"markers": markers, "count": len(markers), "caveat": "Markers include confidence and truth labels; inferred locations are not precise coordinates."}
