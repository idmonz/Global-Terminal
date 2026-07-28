from __future__ import annotations

from typing import Any


def build_noaa_accessais_status() -> dict[str, Any]:
    return {"provider": "NOAA AccessAIS", "status": "historical-only", "live": False, "ok": True, "caveat": "NOAA AccessAIS is historical-only; no live AIS is displayed."}


def build_aisstream_status(*, api_key_present: bool = False, probe_ok: bool = False) -> dict[str, Any]:
    live = bool(api_key_present and probe_ok)
    return {"provider": "AISStream", "status": "live" if live else "missing-key" if not api_key_present else "probe-failed", "live": live, "ok": live, "caveat": None if live else "AISStream is live only if an API key exists and a live probe succeeds."}


def build_vessel_data_status(*, aisstream_key: bool = False, aisstream_probe_ok: bool = False) -> list[dict[str, Any]]:
    return [build_noaa_accessais_status(), build_aisstream_status(api_key_present=aisstream_key, probe_ok=aisstream_probe_ok)]


def route_vessel_data(source: str, rows: list[dict[str, Any]] | None = None, *, provider_status: dict[str, Any] | None = None) -> dict[str, Any]:
    source_key = str(source or "").lower()
    if "noaa" in source_key:
        return {"source": source, "rows": rows or [], **build_noaa_accessais_status()}
    if "aisstream" in source_key:
        status = provider_status or build_aisstream_status()
        live = bool(status.get("live"))
        return {"source": source, "rows": rows if live else [], **status}
    return {"source": source, "rows": [], "status": "unavailable", "live": False, "ok": False, "caveat": "Unknown vessel source is unavailable."}
