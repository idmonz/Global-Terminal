from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable

import pandas as pd

from .data_status import get_recent_results
from .provider_registry import build_provider_registry, get_provider_definition, provider_capability_matrix, provider_env_status


def _diagnostic(provider: dict[str, Any], *, status: str, latency_ms: float | None = None, error: str | None = None, warning: str | None = None, freshness: str = "unknown") -> dict[str, Any]:
    return {
        "provider": provider["provider_id"],
        "configured": bool(provider["is_configured"]),
        "available": bool(provider["is_available"]),
        "status": status,
        "latency_ms": latency_ms,
        "last_fetch": datetime.now(timezone.utc).isoformat(),
        "error": error,
        "warning": warning,
        "requires_key": bool(provider["requires_key"]),
        "freshness": freshness,
        "caveat": provider["caveat"],
    }


def test_provider_connection(provider_id: str, requester: Callable[[dict[str, Any]], Any] | None = None, *, timeout: int = 6) -> dict[str, Any]:
    provider = get_provider_definition(provider_id)
    if provider is None:
        return _diagnostic({"provider_id": provider_id, "is_configured": False, "is_available": False, "requires_key": False, "caveat": "Unknown provider."}, status="unknown", error="Unknown provider")
    env = provider_env_status(provider_id)
    if (provider["requires_key"] or provider["env_var"]) and not env["configured"]:
        return _diagnostic(provider, status="missing_key", warning=f"Missing optional environment variable: {provider['env_var']}", freshness="missing")
    if requester is None:
        return _diagnostic(provider, status="configured" if provider["is_configured"] else "free_mode", warning="No live probe requested.", freshness="estimated")
    start = perf_counter()
    try:
        response = requester(provider)
        latency = (perf_counter() - start) * 1000
        ok = True
        if isinstance(response, dict) and "ok" in response:
            ok = bool(response["ok"])
        elif hasattr(response, "ok"):
            ok = bool(response.ok)
        return _diagnostic(provider, status="ok" if ok else "error", latency_ms=round(latency, 1), error=None if ok else "Probe returned non-ok status.", freshness="fresh" if ok else "error")
    except Exception as exc:
        return _diagnostic(provider, status="error", latency_ms=round((perf_counter() - start) * 1000, 1), error=str(exc), freshness="error")


def test_all_configured_providers(requester: Callable[[dict[str, Any]], Any] | None = None) -> pd.DataFrame:
    rows = []
    for provider in build_provider_registry():
        if provider["is_configured"] or (provider["free_mode"] and not provider["requires_key"]):
            rows.append(test_provider_connection(provider["provider_id"], requester=requester))
    return pd.DataFrame(rows)


def provider_health_summary(registry: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    providers = registry or build_provider_registry()
    total = len(providers)
    configured = sum(bool(provider["is_configured"]) for provider in providers)
    available = sum(bool(provider["is_available"]) for provider in providers)
    optional_missing = sum(bool(provider["requires_key"] or provider["env_var"]) and not provider["is_configured"] for provider in providers)
    return {
        "total_providers": total,
        "configured": configured,
        "available": available,
        "optional_missing": optional_missing,
        "free_mode_available": sum(bool(provider["free_mode"]) for provider in providers),
        "caveat": "Missing optional keys degrade gracefully; paid providers are not required for base launch.",
    }


def provider_error_table(diagnostics: pd.DataFrame | list[dict[str, Any]]) -> pd.DataFrame:
    frame = diagnostics.copy() if isinstance(diagnostics, pd.DataFrame) else pd.DataFrame(diagnostics)
    if frame.empty:
        return pd.DataFrame(columns=["provider", "status", "error", "warning", "caveat"])
    return frame[(frame.get("error").notna()) | (frame.get("warning").notna())][["provider", "status", "error", "warning", "caveat"]]


def provider_freshness_dashboard() -> pd.DataFrame:
    rows = [result.to_dict() for result in get_recent_results()]
    if not rows:
        return pd.DataFrame(columns=["provider", "source", "status", "age_seconds", "coverage", "warning", "error"])
    return pd.DataFrame(rows)


def provider_latency_probe(provider_id: str, requester: Callable[[dict[str, Any]], Any] | None = None) -> dict[str, Any]:
    return test_provider_connection(provider_id, requester=requester)


def provider_rate_limit_status(provider_id: str) -> dict[str, Any]:
    provider = get_provider_definition(provider_id) or {}
    return {
        "provider": provider_id,
        "rate_limit_notes": provider.get("rate_limit_notes", "Unknown provider."),
        "status": "provider-specific",
        "caveat": "This app does not bypass provider rate limits.",
    }


def provider_gap_report() -> pd.DataFrame:
    frame = provider_capability_matrix()
    if frame.empty:
        return pd.DataFrame()
    frame["gap_type"] = frame.apply(lambda row: "missing_key" if (row["requires_key"] or row["env_var"]) and not row["is_configured"] else "available", axis=1)
    return frame[["provider_id", "name", "domain", "gap_type", "env_var", "paid_optional", "caveat"]].sort_values(["gap_type", "domain", "provider_id"])
