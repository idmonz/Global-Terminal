from __future__ import annotations
from typing import Any


def score_match(match_dimensions: set[str]) -> tuple[float, str]:
    dims = set(match_dimensions or set())
    if "exact_symbol" in dims:
        return 0.98, "exact"
    if "alias" in dims and ("region" in dims or "theme" in dims):
        return 0.86, "alias"
    if "alias" in dims:
        return 0.74, "alias"
    if "region" in dims or "country" in dims:
        return 0.64, "inferred"
    if "tag" in dims or "theme" in dims:
        return 0.52, "inferred"
    return 0.25, "low_confidence"


def confidence_label(score: float) -> str:
    if score >= 0.9:
        return "exact"
    if score >= 0.7:
        return "alias"
    if score >= 0.5:
        return "inferred"
    return "timeline_only"
