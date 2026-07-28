from __future__ import annotations

from typing import Any

from .source_freshness_strip import build_provider_caveat_chips, summarize_source_quality


def build_provider_caveat_panel(provider_rows: list[dict[str, Any]] | None = None, *, title: str = "Provider caveats") -> dict[str, Any]:
    chips = build_provider_caveat_chips(provider_rows or [])
    return {
        "title": title,
        "chips": chips,
        "summary": summarize_source_quality(chips),
        "caveats": [chip["caveat"] for chip in chips if chip.get("caveat")],
        "raw_payload_available": True,
        "research_only": True,
    }
