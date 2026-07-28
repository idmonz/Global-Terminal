from __future__ import annotations

from typing import Any

VIEW_PRESETS = [
    {"name": "Global", "region": "Global", "layers": ["macro", "osint", "provider"], "time_window_hours": 24},
    {"name": "Americas", "region": "Americas", "layers": ["macro", "policy", "energy"], "time_window_hours": 24},
    {"name": "Europe", "region": "Europe", "layers": ["macro", "policy", "osint"], "time_window_hours": 24},
    {"name": "MENA", "region": "MENA", "layers": ["energy", "chokepoints", "osint"], "time_window_hours": 12},
    {"name": "East Asia", "region": "East Asia", "layers": ["macro", "shipping", "osint"], "time_window_hours": 24},
    {"name": "Korea", "region": "Korea", "layers": ["macro", "markets", "osint"], "time_window_hours": 24},
    {"name": "Ukraine / Black Sea", "region": "Ukraine / Black Sea", "layers": ["energy", "shipping", "osint"], "time_window_hours": 12},
    {"name": "Red Sea / Suez", "region": "Red Sea / Suez", "layers": ["shipping", "chokepoints", "osint"], "time_window_hours": 12},
    {"name": "Hormuz / Persian Gulf", "region": "Hormuz / Persian Gulf", "layers": ["energy", "shipping", "osint"], "time_window_hours": 12},
    {"name": "Crypto Stress", "region": "Global", "layers": ["crypto", "liquidity", "provider"], "time_window_hours": 6},
    {"name": "Energy Routes", "region": "Global", "layers": ["energy", "shipping", "chokepoints"], "time_window_hours": 24},
    {"name": "Provider Gaps", "region": "Global", "layers": ["provider", "source_freshness"], "time_window_hours": 48},
]


def build_view_presets(selected: str | None = None) -> dict[str, Any]:
    selected_name = selected or "Global"
    presets = [{**preset, "selected": preset["name"] == selected_name, "research_only": True} for preset in VIEW_PRESETS]
    active = next((p for p in presets if p["selected"]), presets[0])
    return {"title": "View presets", "presets": presets, "active": active, "research_only": True}
