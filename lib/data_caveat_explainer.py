from __future__ import annotations

from typing import Any

CAVEAT_EXPLANATIONS = {
    "live": "Current-state label only when confirmed by provider status.",
    "fresh": "Recent source snapshot for research review.",
    "aging": "Source snapshot is getting old; refresh when possible.",
    "stale": "Source snapshot is outdated.",
    "proxy": "Proxy dataset; not a direct measurement.",
    "estimated": "Derived value based on available inputs.",
    "historical-only": "Historical dataset; no current-state claim.",
    "missing-key": "Optional provider credential is not configured.",
    "unavailable": "Provider or panel unavailable.",
    "low-confidence": "Low-confidence source; treat as unconfirmed.",
    "inferred": "Inferred from supplied context and labeled as such.",
}


def explain_data_caveat(label: str) -> dict[str, Any]:
    key = str(label or "unknown").lower().replace("_", "-")
    return {"label": key, "explanation": CAVEAT_EXPLANATIONS.get(key, "Unknown data caveat."), "research_only": True}
