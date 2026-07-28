from __future__ import annotations

from typing import Any


def align_series_by_timestamp(series_by_asset: dict[str, list[dict[str, Any]] | list[float]], *, latest_n: int | None = None) -> dict[str, Any]:
    if not series_by_asset:
        return {"ok": False, "error": "no_series", "research_only": True}
    timestamped = all(isinstance(v, list) and v and isinstance(v[0], dict) and "timestamp" in v[0] for v in series_by_asset.values())
    if not timestamped:
        out = {asset: [float(x) for x in values][-latest_n if latest_n else None:] for asset, values in series_by_asset.items()}  # type: ignore[arg-type]
        return {"ok": True, "aligned": out, "alignment": "latest_n_position", "caveat": "timestamps_not_supplied_latest_n_used", "research_only": True}
    common = set.intersection(*[{str(row.get("timestamp")) for row in rows} for rows in series_by_asset.values()])  # type: ignore[union-attr]
    ordered = sorted(common)
    if latest_n:
        ordered = ordered[-latest_n:]
    aligned: dict[str, list[float]] = {}
    for asset, rows in series_by_asset.items():
        lookup = {str(row.get("timestamp")): float(row.get("value", row.get("price"))) for row in rows}  # type: ignore[union-attr]
        aligned[asset] = [lookup[t] for t in ordered]
    return {"ok": True, "timestamps": ordered, "aligned": aligned, "alignment": "timestamp_intersection", "caveat": "supplied_timestamp_intersection", "research_only": True}
