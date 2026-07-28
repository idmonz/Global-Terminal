from __future__ import annotations

from typing import Any


DEFAULT_SOURCE_PRIORITY = {
    "native": 10,
    "openbb": 20,
    "proxy": 70,
    "static": 80,
    "data_gap": 999,
}


def normalize_provider_name(provider: str | None) -> str:
    return str(provider or "").strip().lower().replace(" ", "_")


def priority_for_source(provider: str | None, *, source_mode: str = "auto", is_proxy: bool = False) -> int:
    provider_name = normalize_provider_name(provider)
    mode = normalize_provider_name(source_mode)
    if provider_name == "openbb":
        base = 5 if mode == "openbb_preferred" else 50 if mode == "native_only" else DEFAULT_SOURCE_PRIORITY["openbb"]
    elif provider_name in {"static", "fallback_static"}:
        base = DEFAULT_SOURCE_PRIORITY["static"]
    elif provider_name in {"data_gap", "unavailable"}:
        base = DEFAULT_SOURCE_PRIORITY["data_gap"]
    else:
        base = DEFAULT_SOURCE_PRIORITY["native"]
    if mode == "openbb_only" and provider_name != "openbb":
        base += 500
    if mode == "native_only" and provider_name == "openbb":
        base += 500
    if is_proxy:
        base = max(base, DEFAULT_SOURCE_PRIORITY["proxy"])
    return base


def sort_sources(candidates: list[dict[str, Any]], *, source_mode: str = "auto") -> list[dict[str, Any]]:
    enriched = []
    for candidate in candidates:
        item = dict(candidate)
        item["priority"] = item.get("priority", priority_for_source(item.get("provider"), source_mode=source_mode, is_proxy=bool(item.get("is_proxy"))))
        enriched.append(item)
    return sorted(enriched, key=lambda row: (int(row.get("priority", 999)), str(row.get("provider", ""))))


def source_confidence_score(*, ok: bool, freshness: str = "unknown", gaps: int = 0, is_proxy: bool = False, is_estimated: bool = False) -> float:
    if not ok:
        return 0.0
    score = 85.0
    if freshness in {"stale", "estimated"}:
        score -= 15.0
    if freshness in {"missing", "error"}:
        score -= 45.0
    score -= min(40.0, float(gaps) * 8.0)
    if is_proxy:
        score -= 20.0
    if is_estimated:
        score -= 10.0
    return round(max(0.0, min(100.0, score)), 1)
