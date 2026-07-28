from __future__ import annotations

from collections import defaultdict
from typing import Any


def _keyed(surface: dict[str, Any]) -> dict[tuple[str, float, str], dict[str, Any]]:
    return {(str(p.get("expiry")), float(p.get("strike")), str(p.get("option_type"))): p for p in surface.get("points", []) if p.get("strike") is not None}


def _avg_by_expiry(points: list[dict[str, Any]]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for p in points:
        if p.get("mid_iv") is not None:
            buckets[str(p.get("expiry"))].append(float(p["mid_iv"]))
    return {k: sum(v) / len(v) for k, v in buckets.items() if v}


def _atm_by_expiry(points: list[dict[str, Any]]) -> dict[str, float | None]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in points:
        if p.get("mid_iv") is not None:
            buckets[str(p.get("expiry"))].append(p)
    out: dict[str, float | None] = {}
    for expiry, rows in buckets.items():
        nearest = min(rows, key=lambda p: abs(float(p.get("moneyness") or 1.0) - 1.0))
        out[expiry] = float(nearest["mid_iv"])
    return out


def build_surface_snapshot_diff(previous_surface: dict[str, Any], current_surface: dict[str, Any], *, tolerance: float = 1e-9) -> dict[str, Any]:
    prev = _keyed(previous_surface)
    cur = _keyed(current_surface)
    changed = []
    for key in sorted(set(prev) & set(cur)):
        old = prev[key].get("mid_iv")
        new = cur[key].get("mid_iv")
        if old is not None and new is not None and abs(float(new) - float(old)) > tolerance:
            changed.append({"expiry": key[0], "strike": key[1], "option_type": key[2], "old_mid_iv": float(old), "new_mid_iv": float(new), "change": float(new) - float(old), "research_only": True})
    return {"ok": True, "previous_point_count": len(prev), "current_point_count": len(cur), "expiry_set_previous": sorted({k[0] for k in prev}), "expiry_set_current": sorted({k[0] for k in cur}), "strike_set_previous": sorted({k[1] for k in prev}), "strike_set_current": sorted({k[1] for k in cur}), "average_iv_by_expiry_previous": _avg_by_expiry(previous_surface.get("points", [])), "average_iv_by_expiry_current": _avg_by_expiry(current_surface.get("points", [])), "atm_iv_by_expiry_previous": _atm_by_expiry(previous_surface.get("points", [])), "atm_iv_by_expiry_current": _atm_by_expiry(current_surface.get("points", [])), "changed_rows": changed, "new_rows": [list(k) for k in sorted(set(cur) - set(prev))], "newly_missing_rows": [list(k) for k in sorted(set(prev) - set(cur))], "research_only": True}


def build_surface_change_summary(diff_payload: dict[str, Any]) -> dict[str, Any]:
    changes = [abs(float(r.get("change", 0))) for r in diff_payload.get("changed_rows", [])]
    return {"ok": True, "changed_row_count": len(changes), "new_row_count": len(diff_payload.get("new_rows", [])), "missing_row_count": len(diff_payload.get("newly_missing_rows", [])), "max_abs_iv_change": max(changes) if changes else 0.0, "research_only": True}
