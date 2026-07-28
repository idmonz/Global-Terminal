from __future__ import annotations

from typing import Any

from .view_preset_engine import VIEW_PRESETS, build_view_presets


def build_research_view_presets(selected: str | None = None) -> dict[str, Any]:
    return build_view_presets(selected)
