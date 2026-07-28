from __future__ import annotations

from typing import Any


def build_methodology_tooltip_payload(
    panel: str,
    *,
    method: str = "Source-driven research panel",
    inputs: list[str] | None = None,
    caveats: list[str] | None = None,
    refresh_policy: str = "Manual refresh unless provider integration states otherwise.",
) -> dict[str, Any]:
    return {
        "panel": panel,
        "method": method,
        "inputs": inputs or [],
        "caveats": caveats or ["Raw provider payloads are shown only in expanders."],
        "refresh_policy": refresh_policy,
        "research_only": True,
    }
