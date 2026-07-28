from __future__ import annotations

from typing import Any


def build_noaa_accessais_metadata() -> dict[str, Any]:
    return {
        "provider": "noaa_accessais",
        "status": "historical_only",
        "source_type": "official_historical_only",
        "label": "NOAA AccessAIS historical archive",
        "caveat": "Historical-only source; no live AIS is claimed.",
    }


def fetch_noaa_accessais_catalog(*, dry_run: bool = True) -> dict[str, Any]:
    metadata = build_noaa_accessais_metadata()
    return {**metadata, "ok": True, "dry_run": dry_run, "data": []}
