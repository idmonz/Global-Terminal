from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .env_loader import get_env_var, load_project_env
from .no_key_provider_catalog import list_no_key_providers


def build_probe_plan(provider_ids: list[str] | None = None) -> list[dict[str, Any]]:
    load_project_env()
    selected = set(provider_ids or [])
    providers = list_no_key_providers()
    if selected:
        providers = [item for item in providers if item["provider_id"] in selected]
    return providers


def build_probe_registry(provider_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Compatibility wrapper for the canonical Goal 10 probe registry API."""
    return build_probe_plan(provider_ids)


def _provider_configured(provider: dict[str, Any]) -> bool:
    env_vars = [part.strip() for part in str(provider.get("env_var", "")).split(",") if part.strip()]
    if not env_vars:
        return True
    return all(get_env_var(env) for env in env_vars)


def probe_provider(provider: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
    configured = _provider_configured(provider)
    historical_only = provider["provider_id"] == "noaa_accessais"
    if provider["provider_id"] == "opensky" and not dry_run:
        from .opensky_provider import fetch_opensky_access_token

        token, token_status = fetch_opensky_access_token()
        return {
            "provider_id": provider["provider_id"],
            "provider": provider["name"],
            "ok": bool(token and token_status.ok),
            "status": "oauth_verified" if token and token_status.ok else token_status.refreshed_status(),
            "configured": configured,
            "dry_run": dry_run,
            "source_type": provider.get("source_type"),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "warning": token_status.warning,
            "error": token_status.error,
            "caveat": "OpenSky probe verifies OAuth2 client credentials without spending /states/all credits.",
        }
    status = "dry_run" if dry_run else "available"
    if historical_only:
        status = "historical_only"
    elif provider.get("key_required") and not configured:
        status = "missing_key"
    elif not configured:
        status = "no_key_fallback" if provider.get("no_key_fallback") else "missing_key"
    return {
        "provider_id": provider["provider_id"],
        "provider": provider["name"],
        "ok": status not in {"missing_key"},
        "status": status,
        "configured": configured,
        "dry_run": dry_run,
        "source_type": provider.get("source_type"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "warning": provider.get("caveat") if status in {"missing_key", "historical_only", "no_key_fallback"} else None,
    }


def run_provider_probe(provider: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
    """Compatibility wrapper for callers that probe one registry entry."""
    return probe_provider(provider, dry_run=dry_run)


def run_provider_probes(provider_ids: list[str] | None = None, *, dry_run: bool = True, save: bool = False) -> list[dict[str, Any]]:
    load_project_env()
    results = [probe_provider(provider, dry_run=dry_run) for provider in build_probe_plan(provider_ids)]
    if save:
        from .provider_probe_store import save_provider_probe_results

        save_provider_probe_results(results)
    return results


def run_all_lightweight_probes(*, dry_run: bool = True, save: bool = False) -> list[dict[str, Any]]:
    """Run the lightweight no-key/free-key probe matrix."""
    return run_provider_probes(dry_run=dry_run, save=save)


def build_probe_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    ready = sum(1 for item in results if item.get("ok"))
    gaps = sum(1 for item in results if item.get("status") == "missing_key")
    return {"total": total, "ready": ready, "gaps": gaps, "status": "gaps" if gaps else "available"}


def build_provider_probe_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compatibility wrapper for the canonical Goal 10 provider summary API."""
    return build_probe_summary(results)
