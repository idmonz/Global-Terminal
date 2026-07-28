from __future__ import annotations
from typing import Any
from .options_vol_surface import build_surface_heatmap_payload

def build_options_surface_visual_payload(surface_snapshot: dict[str, Any]) -> dict[str, Any]:
    payload = build_surface_heatmap_payload(surface_snapshot)
    return {**payload, "chart_type": "heatmap", "caveat": "Visual payload uses supplied chain points only; interpolation is labeled separately.", "research_only": True}
