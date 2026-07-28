from __future__ import annotations

import os
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from .data_contracts import DataGap, DataRequest, DataRoute, ProviderCapability
from .endpoint_catalog import build_internal_endpoint_catalog, get_endpoint_definition
from .openbb_bridge import is_openbb_installed
from .source_priority import priority_for_source, sort_sources


def _native_route(provider: str, endpoint: str, *, app_area: str = "", priority: int = 10, caveat: str = "", supports_proxy: bool = False) -> ProviderCapability:
    return ProviderCapability(provider=provider, endpoint=endpoint, app_area=app_area, native=True, openbb=False, priority=priority, caveat=caveat, supports_proxy=supports_proxy)


def _openbb_route(endpoint: str, *, app_area: str = "", priority: int = 20, requires_key: bool = False, caveat: str = "") -> ProviderCapability:
    return ProviderCapability(provider="openbb", endpoint=endpoint, app_area=app_area, native=False, openbb=True, requires_key=requires_key, priority=priority, caveat=caveat or "OpenBB is optional and provider availability varies by installation.")


def build_provider_route_table() -> list[ProviderCapability]:
    catalog = build_internal_endpoint_catalog()
    routes: list[ProviderCapability] = []
    for endpoint_id, definition in catalog.items():
        for provider in definition.native_providers:
            routes.append(_native_route(provider, endpoint_id, app_area=definition.app_area, priority=priority_for_source(provider), caveat=definition.caveat, supports_proxy=definition.proxy_allowed))
        if definition.openbb_candidate_paths:
            routes.append(_openbb_route(endpoint_id, app_area=definition.app_area, requires_key=bool(definition.optional_provider_keys), caveat=definition.caveat))
        if definition.proxy_allowed and "proxy" not in definition.native_providers:
            routes.append(_native_route("proxy", endpoint_id, app_area=definition.app_area, priority=70, caveat=definition.caveat, supports_proxy=True))
        routes.append(_native_route("data_gap", endpoint_id, app_area=definition.app_area, priority=999, caveat=definition.caveat))
    return routes


def _routes_for_endpoint(endpoint: str) -> list[ProviderCapability]:
    return [route for route in build_provider_route_table() if route.endpoint == endpoint]


def _configured_keys(keys: list[str]) -> list[str]:
    return [key for key in keys if os.getenv(key)]


def provider_missing_key_gaps(endpoint: str, provider: str | None = None) -> list[DataGap]:
    definition = get_endpoint_definition(endpoint)
    if not definition:
        return [DataGap(field=endpoint, reason="Unknown endpoint.", severity="high", provider=provider, endpoint=endpoint, is_blocking=True)]
    missing = [key for key in definition.optional_provider_keys if not os.getenv(key)]
    return [DataGap(field=key, reason="Optional provider key is not configured; no secret value is displayed.", severity="medium", provider=provider or "openbb", endpoint=endpoint, is_blocking=False) for key in missing]


def rank_provider_candidates(request: DataRequest | dict[str, Any]) -> list[ProviderCapability]:
    req = request if isinstance(request, DataRequest) else DataRequest(**request)
    routes = _routes_for_endpoint(req.endpoint)
    definition = get_endpoint_definition(req.endpoint)
    candidates: list[dict[str, Any]] = []
    for route in routes:
        if req.provider_preference and route.provider != req.provider_preference and req.source_mode == "provider_specific":
            continue
        if req.source_mode == "native_only" and route.openbb:
            continue
        if req.source_mode == "openbb_only" and not route.openbb and route.provider != "data_gap":
            continue
        if route.provider == "proxy" and not req.allow_proxy:
            continue
        priority = route.priority
        if route.openbb:
            priority = priority_for_source("openbb", source_mode=req.source_mode)
            if not is_openbb_installed():
                priority += 250 if req.source_mode != "openbb_only" else 25
        elif route.provider == "data_gap":
            priority = 999
        else:
            priority = priority_for_source(route.provider, source_mode=req.source_mode, is_proxy=route.provider == "proxy")
        if req.provider_preference and route.provider == req.provider_preference:
            priority -= 8
        if definition and route.openbb and definition.optional_provider_keys and not _configured_keys(definition.optional_provider_keys):
            priority += 12
        row = route.to_dict()
        row["priority"] = priority
        candidates.append(row)
    return [ProviderCapability(**row) for row in sort_sources(candidates, source_mode=req.source_mode)]


def select_provider_for_request(request: DataRequest | dict[str, Any]) -> DataRoute:
    req = request if isinstance(request, DataRequest) else DataRequest(**request)
    candidates = rank_provider_candidates(req)
    if not candidates:
        return DataRoute(provider="data_gap", endpoint=req.endpoint, source="provider router", native=False, warning="No provider candidates matched request constraints.", rank=999)
    selected = candidates[0]
    definition = get_endpoint_definition(req.endpoint)
    missing_keys = [gap.field for gap in provider_missing_key_gaps(req.endpoint, selected.provider)] if selected.openbb and definition else []
    warning = None
    if selected.openbb and not is_openbb_installed():
        warning = "OpenBB is not installed; native fallback remains available when source mode allows it."
    if selected.provider == "data_gap":
        warning = "No configured provider can satisfy this endpoint."
    source = "optional OpenBB bridge" if selected.openbb else f"native {selected.provider}" if selected.native else selected.provider
    return DataRoute(
        provider=selected.provider,
        endpoint=req.endpoint,
        source=source,
        native=selected.native and selected.provider not in {"data_gap", "proxy"},
        openbb=selected.openbb,
        fallback_chain=fallback_provider_chain(req),
        missing_keys=missing_keys,
        warning=warning,
        caveat=selected.caveat,
        rank=selected.priority,
    )


def resolve_provider_route(request: DataRequest | dict[str, Any]) -> DataRoute:
    return select_provider_for_request(request)


def fallback_provider_chain(request: DataRequest | dict[str, Any]) -> list[str]:
    req = request if isinstance(request, DataRequest) else DataRequest(**request)
    return [candidate.provider for candidate in rank_provider_candidates(req) if candidate.provider != "data_gap"]


def provider_capability_for_endpoint(endpoint: str, provider: str | None = None) -> ProviderCapability | None:
    routes = _routes_for_endpoint(endpoint)
    if provider:
        return next((route for route in routes if route.provider == provider), None)
    return routes[0] if routes else None


def provider_unavailable_warning(provider: str, endpoint: str, reason: str | None = None) -> str:
    detail = f": {reason}" if reason else "."
    return f"{provider} is unavailable for {endpoint}{detail}"


def provider_route_table_frame():
    rows = [route.to_dict() for route in build_provider_route_table()]
    return pd.DataFrame(rows) if pd is not None else rows
