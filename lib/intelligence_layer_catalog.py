from __future__ import annotations

from typing import Any

from .layer_panel_payload import LAYER_CATALOG, build_layer_panel_payload


def build_intelligence_layer_catalog() -> dict[str, Any]:
    return {"title": "Intelligence layer catalog", "layers": [{**row, "research_only": True} for row in LAYER_CATALOG], "research_only": True}
