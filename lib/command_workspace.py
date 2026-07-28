from __future__ import annotations

import hashlib
from typing import Any, Iterable

from .event_asset_graph import EVIDENCE_REFS as EVENT_GRAPH_EVIDENCE_REFS
from .event_asset_graph import build_event_asset_graph_contract
from .provider_health_engine import classify_provider_ledger_status, recommended_action_for_status


COMMAND_WORKSPACE_VERSION = "command_workspace.v1"

AVAILABLE_PROVIDER_STATUSES = {"live/fresh", "cached"}
LIMITED_PROVIDER_STATUSES = {"stale", "rate-limited", "proxy/static", "fixture"}
BLOCKED_PROVIDER_STATUSES = {"missing-key", "forbidden/subscription-blocked", "unavailable"}

RESEARCH_ONLY_NOTICE = (
    "Research workstation action only; source labels, provider status, caveats, and data gaps must be reviewed before use."
)

COMMAND_DEFINITIONS: list[dict[str, Any]] = [
    {
        "command": "NI",
        "label": "News Intelligence",
        "description": "Inspect source-backed news and event context tied to the active graph node.",
        "accepted_context_types": ["event", "region", "risk_theme", "asset", "provider", "graph"],
        "provider_family": "news",
        "provider_keywords": ["gdelt", "rss", "news", "live_feeds", "fixture"],
        "requires_provider": True,
        "implementation_status": "schema-ready/source-backed-news-required",
        "default_source_status": "provider-required",
        "freshness": "provider-gated",
        "route": "/api/market-intelligence",
        "workspace_view": "market-intelligence",
        "caveat": "Routes to source-labeled news/event rows; does not produce directional market advice.",
        "data_gap": "Needs fresh or cached news/event provider evidence before being marked available.",
    },
    {
        "command": "MAP",
        "label": "War Room Map",
        "description": "Open map/layer context for events, regions, and source-status-aware overlays.",
        "accepted_context_types": ["event", "region", "risk_theme", "provider", "graph"],
        "provider_family": "map_layers",
        "provider_keywords": ["war_room", "layer", "usgs", "static", "fixture", "chokepoint"],
        "requires_provider": False,
        "implementation_status": "schema-ready/proxy-layer-aware",
        "default_source_status": "proxy/static",
        "freshness": "proxy/static",
        "route": "/api/war-room-map",
        "workspace_view": "war-room-map",
        "caveat": "Map context may use approximate coordinates, fixture rows, or static/proxy chokepoints unless live layers are present.",
        "data_gap": "Live AIS/flight/advanced map layers remain unavailable unless separately configured and probed.",
    },
    {
        "command": "DES",
        "label": "Description",
        "description": "Resolve security or asset description fields for a selected asset context.",
        "accepted_context_types": ["asset", "asset_class", "ticker", "graph"],
        "provider_family": "asset_profile",
        "provider_keywords": ["openbb", "fmp", "finnhub", "sec", "asset_universe"],
        "requires_provider": True,
        "implementation_status": "schema-ready/provider-required",
        "default_source_status": "reference-schema",
        "freshness": "provider-gated",
        "route": "/api/equity-intelligence",
        "workspace_view": "financial-fundamentals",
        "caveat": "Asset description routing is schema-ready; live descriptions need provider-backed rows.",
        "data_gap": "No bundled live security master or profile rows are claimed.",
    },
    {
        "command": "FA",
        "label": "Fundamental Analysis",
        "description": "Inspect provider-backed financial statement and ratio availability for equities.",
        "accepted_context_types": ["asset", "equity", "ticker", "provider"],
        "provider_family": "fundamentals",
        "provider_keywords": ["openbb", "fmp", "finnhub", "sec", "edgar", "fundamental"],
        "requires_provider": True,
        "implementation_status": "future-provider-required",
        "default_source_status": "provider-required",
        "freshness": "provider-gated",
        "route": "/api/equity-intelligence",
        "workspace_view": "equity-intelligence",
        "caveat": "Financial statement commands require provider-backed fundamentals and remain non-advisory.",
        "data_gap": "No live fundamentals provider evidence is bundled in deterministic fixtures.",
    },
    {
        "command": "GP",
        "label": "Graph / Price",
        "description": "Inspect price-chart readiness for the active market context.",
        "accepted_context_types": ["asset", "commodity", "fx_pair", "crypto_pair", "index", "ticker"],
        "provider_family": "price",
        "provider_keywords": ["openbb", "yfinance", "stooq", "coingecko", "binance", "polygon", "fmp", "alpha_vantage"],
        "requires_provider": True,
        "implementation_status": "provider-required",
        "default_source_status": "provider-required",
        "freshness": "provider-gated",
        "route": "/api/equity-intelligence",
        "workspace_view": "equity-intelligence",
        "caveat": "Price graph commands require fresh or cached market data with source labels.",
        "data_gap": "No price chart is marked available without market-data provider evidence.",
    },
    {
        "command": "HP",
        "label": "Historical Price",
        "description": "Inspect historical price readiness and freshness for the active market context.",
        "accepted_context_types": ["asset", "commodity", "fx_pair", "crypto_pair", "index", "ticker"],
        "provider_family": "price_history",
        "provider_keywords": ["openbb", "yfinance", "stooq", "coingecko", "binance", "polygon", "fmp", "alpha_vantage"],
        "requires_provider": True,
        "implementation_status": "provider-required",
        "default_source_status": "provider-required",
        "freshness": "provider-gated",
        "route": "/api/equity-intelligence",
        "workspace_view": "equity-intelligence",
        "caveat": "Historical price commands require provider-backed time series and source freshness.",
        "data_gap": "No historical price series is emitted without provider evidence.",
    },
    {
        "command": "WEI",
        "label": "Weights / Exposure",
        "description": "Inspect holdings, constituent, and exposure-command readiness for funds or indices.",
        "accepted_context_types": ["asset", "etf", "fund", "index", "sector"],
        "provider_family": "holdings",
        "provider_keywords": ["openbb", "fmp", "holdings", "constituent", "etf"],
        "requires_provider": True,
        "implementation_status": "future-provider-required",
        "default_source_status": "provider-required",
        "freshness": "provider-gated",
        "route": "/api/provider-health",
        "workspace_view": "provider-health",
        "caveat": "Exposure commands require provider-backed holdings or constituent rows.",
        "data_gap": "No ETF/index holdings or weights are bundled in this slice.",
    },
    {
        "command": "CURV",
        "label": "Rates Curve",
        "description": "Inspect rates/yield-curve provider readiness for macro contexts.",
        "accepted_context_types": ["macro", "rates", "fx_pair", "region", "provider"],
        "provider_family": "rates",
        "provider_keywords": ["fred", "treasury", "openbb", "sdmx", "rates", "yield"],
        "requires_provider": True,
        "implementation_status": "schema-ready/provider-required",
        "default_source_status": "provider-required",
        "freshness": "provider-gated",
        "route": "/api/provider-health",
        "workspace_view": "provider-health",
        "caveat": "Rates curve commands require source-labeled rates data and freshness metadata.",
        "data_gap": "No live rates curve provider evidence is bundled in deterministic fixtures.",
    },
    {
        "command": "FXC",
        "label": "FX Crosses",
        "description": "Inspect FX cross readiness for the active currency or macro context.",
        "accepted_context_types": ["fx_pair", "currency", "macro", "region", "provider"],
        "provider_family": "fx",
        "provider_keywords": ["openbb", "yfinance", "fred", "currency", "fx", "forex"],
        "requires_provider": True,
        "implementation_status": "schema-ready/provider-required",
        "default_source_status": "reference-schema",
        "freshness": "provider-gated",
        "route": "/api/asset-universe",
        "workspace_view": "asset-universe",
        "caveat": "FX routing is schema-ready; live FX quotes require provider evidence.",
        "data_gap": "No live FX quote provider is claimed by the command workspace fixture.",
    },
    {
        "command": "CRYPTO",
        "label": "Crypto Market",
        "description": "Inspect public crypto provider readiness for crypto pairs and liquidity context.",
        "accepted_context_types": ["crypto_pair", "asset", "provider", "event"],
        "provider_family": "crypto",
        "provider_keywords": ["coingecko", "binance", "crypto"],
        "requires_provider": True,
        "implementation_status": "schema-ready/provider-required",
        "default_source_status": "provider-required",
        "freshness": "provider-gated",
        "route": "/api/crypto-intelligence",
        "workspace_view": "crypto-intelligence",
        "caveat": "Crypto commands can use public CoinGecko/Binance-style provider states when available; no account or exchange action is added.",
        "data_gap": "No crypto result is marked available unless a public crypto provider is fresh or cached.",
    },
    {
        "command": "OMON",
        "label": "Options Monitor",
        "description": "Inspect options chain, concentration, and gamma-proxy readiness for an equity context.",
        "accepted_context_types": ["asset", "equity", "ticker", "provider"],
        "provider_family": "options",
        "provider_keywords": ["openbb", "yfinance options", "options", "chain", "volatility"],
        "requires_provider": True,
        "implementation_status": "schema-ready/provider-required",
        "default_source_status": "provider-required",
        "freshness": "provider-gated",
        "route": "/api/equity-intelligence",
        "workspace_view": "options-quant",
        "caveat": "Options monitor opens a provider-gated readiness surface; no dealer-position or execution path is implied.",
        "data_gap": "Options chain rows remain unavailable unless a fresh or cached options provider is present.",
    },
]


PHASE3_EVIDENCE_REFS = [
    {
        "external_project": "BB-Terminal",
        "evidence_ref": "Phase 2E BB-Terminal command-workstation evidence card",
        "license_stance": "blocked/direct-copy-not-used",
        "usage": "Dense command bar and workspace-state behavior reference only.",
        "copied_source": False,
        "local_target": "lib/command_workspace.py and apps/web command-workspace view",
        "required_tests": ["tests/test_command_workspace_contracts.py"],
        "product_value": "Terminal-style command suggestions become auditable provider-gated actions.",
        "caveat": "No source, component structure, or styling is copied.",
    },
    {
        "external_project": "OpenBB",
        "evidence_ref": "OpenBB-develop/openbb_platform/core/openbb_core/api/router/commands.py",
        "license_stance": "behavior-only/agpl-boundary",
        "usage": "Provider command-contract mental model only.",
        "copied_source": False,
        "local_target": "provider-gated command result envelopes",
        "required_tests": ["tests/test_command_workspace_contracts.py"],
        "product_value": "Keeps command availability tied to provider status instead of UI claims.",
        "caveat": "OpenBB remains optional and is not vendored or added as a dependency.",
    },
    {
        "external_project": "WorldMonitor",
        "evidence_ref": "Phase 2E WorldMonitor provider-health evidence card",
        "license_stance": "behavior-only/agpl-boundary",
        "usage": "Source/provenance/status/caveat discipline for every command.",
        "copied_source": False,
        "local_target": "command source-status and caveat rail",
        "required_tests": ["tests/test_command_workspace_contracts.py"],
        "product_value": "Unavailable and stale states remain visible beside available source context.",
        "caveat": "AGPL source is not copied.",
    },
    {
        "external_project": "Supabase",
        "evidence_ref": "supabase-master/README.md:9-16",
        "license_stance": "architecture-reference-only",
        "usage": "Future workspace persistence/readiness reference only.",
        "copied_source": False,
        "local_target": "readiness.unavailable_capabilities",
        "required_tests": ["tests/test_command_workspace_contracts.py"],
        "product_value": "Shows persistence/auth/billing as unavailable in this slice.",
        "caveat": "No hosted persistence, auth, account, billing, or database dependency is added.",
    },
    {
        "external_project": "FinanceDatabase",
        "evidence_ref": "FinanceDatabase-main/database/equities/NMS.csv:1-1 and related Phase 2E schema evidence",
        "license_stance": "direct-use-allowed/schema-only",
        "usage": "Asset-class and command-routing taxonomy behavior.",
        "copied_source": False,
        "local_target": "accepted_context_types and schema-ready command gaps",
        "required_tests": ["tests/test_command_workspace_contracts.py"],
        "product_value": "Keeps DES/FA/WEI/FXC/CRYPTO routing tied to asset-class schemas.",
        "caveat": "No external CSV rows are copied.",
    },
]


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ["data", "ledger", "provider_rows", "rows", "source_status"]:
            if isinstance(value.get(key), list):
                return _records(value.get(key))
        return [dict(value)]
    return []


def _normalize_status(value: Any) -> str:
    status = str(value or "").strip().lower().replace("_", "-")
    if not status:
        return "provider-required"
    if status in {"fresh", "available", "ok", "live"}:
        return "live/fresh"
    if status in {"configured", "contacted"}:
        return status
    if status in {"fixture", "static"}:
        return "fixture"
    if status in {"missing", "missing-key"}:
        return "missing-key"
    if status in {"error", "unavailable", "failed"}:
        return "unavailable"
    if "forbidden" in status or "subscription" in status or "unauthorized" in status:
        return "forbidden/subscription-blocked"
    if "rate" in status and "limit" in status:
        return "rate-limited"
    if "proxy" in status or "static" in status:
        return "proxy/static"
    return status


def _provider_name(row: dict[str, Any]) -> str:
    return str(row.get("provider") or row.get("source") or row.get("node_id") or "none")


def _provider_status(row: dict[str, Any]) -> str:
    status = row.get("status") or row.get("source_status") or row.get("freshness") or row.get("freshness_status")
    if status:
        return _normalize_status(status)
    try:
        return _normalize_status(classify_provider_ledger_status(row))
    except Exception:
        return "unavailable"


def _status_rank(status: str) -> int:
    status = _normalize_status(status)
    ranking = {
        "live/fresh": 0,
        "cached": 1,
        "stale": 2,
        "rate-limited": 3,
        "fixture": 4,
        "proxy/static": 5,
        "missing-key": 6,
        "forbidden/subscription-blocked": 7,
        "unavailable": 8,
        "provider-required": 9,
        "contacted": 9,
        "configured": 10,
    }
    return ranking.get(status, 10)


def _text(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(key) or "") for key in ["provider", "source", "coverage", "caveat", "warning", "error", "node_id"]).lower()


def _row_matches_keywords(row: dict[str, Any], keywords: Iterable[str]) -> bool:
    text = _text(row)
    return any(str(keyword).lower() in text for keyword in keywords)


def _dedupe_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = "|".join(str(row.get(part) or "") for part in ["provider", "source", "status", "source_status", "node_id"])
        if key not in deduped:
            deduped[key] = dict(row)
    return list(deduped.values())


def _provider_rows_from_graph(event_graph: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in _records(event_graph.get("nodes")):
        if node.get("type") == "provider":
            rows.append(
                {
                    "provider": node.get("provider") or node.get("label"),
                    "source": node.get("source_url") or node.get("id"),
                    "status": node.get("source_status"),
                    "availability": "available" if _normalize_status(node.get("source_status")) in AVAILABLE_PROVIDER_STATUSES else "limited",
                    "row_count": node.get("metadata", {}).get("row_count") if isinstance(node.get("metadata"), dict) else None,
                    "fetched_at": node.get("fetched_at"),
                    "warning": node.get("caveat"),
                    "error": node.get("data_gap"),
                    "caveat": node.get("caveat"),
                    "node_id": node.get("id"),
                }
            )
        if node.get("type") == "event":
            rows.append(
                {
                    "provider": node.get("provider") or "event_source",
                    "source": node.get("source_url") or node.get("id"),
                    "status": node.get("source_status"),
                    "availability": "available" if _normalize_status(node.get("source_status")) in AVAILABLE_PROVIDER_STATUSES else "limited",
                    "row_count": 1,
                    "fetched_at": node.get("fetched_at"),
                    "warning": node.get("caveat"),
                    "error": node.get("data_gap"),
                    "caveat": node.get("caveat"),
                    "node_id": node.get("id"),
                    "node_type": "event",
                }
            )
    return rows


def _select_provider_requirement(definition: dict[str, Any], provider_rows: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [row for row in provider_rows if _row_matches_keywords(row, definition.get("provider_keywords", []))]
    if definition["command"] == "NI":
        matched.extend(row for row in provider_rows if row.get("node_type") == "event")
    if definition["command"] == "MAP":
        matched.extend(row for row in provider_rows if str(row.get("status") or row.get("source_status")) in {"proxy/static", "fixture"})
    matched = _dedupe_rows(matched)
    if not matched:
        return {
            "command": definition["command"],
            "provider_family": definition["provider_family"],
            "provider": "none",
            "status": "provider-required" if definition.get("requires_provider") else definition["default_source_status"],
            "source": "",
            "fetched_at": None,
            "row_count": 0,
            "recommended_action": "Configure or surface a source-backed provider before marking this command available.",
            "caveat": definition["data_gap"],
        }
    selected = sorted(matched, key=lambda row: _status_rank(_provider_status(row)))[0]
    status = _provider_status(selected)
    return {
        "command": definition["command"],
        "provider_family": definition["provider_family"],
        "provider": _provider_name(selected),
        "status": status,
        "source": selected.get("source") or selected.get("source_url") or selected.get("node_id") or "",
        "fetched_at": selected.get("fetched_at"),
        "row_count": selected.get("row_count"),
        "recommended_action": selected.get("recommended_action") or recommended_action_for_status(status),
        "caveat": selected.get("caveat") or selected.get("warning") or definition["caveat"],
    }


def _status_for_command(definition: dict[str, Any], provider_requirement: dict[str, Any], *, has_context: bool) -> tuple[str, bool, str]:
    status = _normalize_status(provider_requirement.get("status"))
    command = definition["command"]
    if definition.get("requires_provider") and status in AVAILABLE_PROVIDER_STATUSES:
        return "available", True, status
    if command == "NI" and status in {"fixture", "proxy/static"} and has_context:
        return "source-backed-preview", False, status
    if command == "MAP" and has_context:
        if status in AVAILABLE_PROVIDER_STATUSES:
            return "available", True, status
        return "proxy/static", False, "proxy/static"
    if definition.get("requires_provider"):
        if status in BLOCKED_PROVIDER_STATUSES or status in LIMITED_PROVIDER_STATUSES:
            return status if status in BLOCKED_PROVIDER_STATUSES else "provider-required", False, status
        return "provider-required", False, status
    if has_context:
        return definition["default_source_status"], False, definition["default_source_status"]
    return "unavailable", False, "unavailable"


def _context_id(seed: str) -> str:
    return f"context:{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:14]}"


def _command_suggestion_contexts(event_graph: dict[str, Any]) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    nodes = {str(node.get("id")): node for node in _records(event_graph.get("nodes"))}
    for suggestion in _records(event_graph.get("command_suggestions")):
        command = str(suggestion.get("command") or "").upper()
        event_node_ids = [str(node_id) for node_id in suggestion.get("related_event_node_ids") or []]
        contexts.append(
            {
                "context_id": _context_id(f"command|{command}|{','.join(event_node_ids)}"),
                "context_type": "command_suggestion",
                "source": "phase2f_event_asset_graph",
                "command": command,
                "label": suggestion.get("label") or command,
                "source_status": suggestion.get("source_status") or "reference-schema",
                "confidence": suggestion.get("confidence"),
                "related_event_node_ids": event_node_ids,
                "caveat": suggestion.get("caveat") or "",
            }
        )
        for event_node_id in event_node_ids:
            node = nodes.get(event_node_id, {})
            contexts.append(
                {
                    "context_id": _context_id(f"event|{event_node_id}|{command}"),
                    "context_type": "event",
                    "source": "phase2f_event_asset_graph",
                    "command": command,
                    "node_id": event_node_id,
                    "label": node.get("label") or event_node_id,
                    "source_status": node.get("source_status") or "unknown",
                    "provider": node.get("provider") or "",
                    "fetched_at": node.get("fetched_at"),
                    "caveat": node.get("caveat") or "",
                    "data_gap": node.get("data_gap") or "",
                }
            )
    for node in nodes.values():
        if node.get("type") in {"commodity", "fx_pair", "crypto_pair", "asset_class", "sector", "region", "provider"}:
            contexts.append(
                {
                    "context_id": _context_id(f"{node.get('type')}|{node.get('id')}"),
                    "context_type": str(node.get("type")),
                    "source": "phase2f_event_asset_graph",
                    "command": "",
                    "node_id": node.get("id"),
                    "label": node.get("label"),
                    "source_status": node.get("source_status"),
                    "provider": node.get("provider") or "",
                    "fetched_at": node.get("fetched_at"),
                    "caveat": node.get("caveat") or "",
                    "data_gap": node.get("data_gap") or "",
                }
            )
    deduped: dict[str, dict[str, Any]] = {}
    for context in contexts:
        deduped[str(context["context_id"])] = context
    return sorted(deduped.values(), key=lambda item: (str(item.get("context_type")), str(item.get("label") or item.get("command") or "")))


def _command_has_context(command: str, contexts: list[dict[str, Any]]) -> bool:
    if command == "MAP":
        return any(context.get("context_type") in {"event", "region"} for context in contexts)
    return any(context.get("command") == command for context in contexts)


def _build_command_record(definition: dict[str, Any], result_status: str, source_status: str, provider_requirement: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": definition["command"],
        "label": definition["label"],
        "description": definition["description"],
        "accepted_context_types": list(definition["accepted_context_types"]),
        "provider": provider_requirement.get("provider") or "none",
        "provider_family": definition["provider_family"],
        "source_status": source_status,
        "freshness": definition.get("freshness") if source_status not in AVAILABLE_PROVIDER_STATUSES else source_status,
        "fetched_at": provider_requirement.get("fetched_at"),
        "implementation_status": definition["implementation_status"],
        "requires_provider": bool(definition["requires_provider"]),
        "result_status": result_status,
        "route": definition["route"],
        "workspace_view": definition["workspace_view"],
        "caveat": definition["caveat"],
        "data_gap": definition["data_gap"],
        "not_financial_advice": True,
    }


def _build_command_result(
    definition: dict[str, Any],
    command: dict[str, Any],
    provider_requirement: dict[str, Any],
    *,
    available: bool,
    result_status: str,
) -> dict[str, Any]:
    enabled = available or result_status in {"source-backed-preview", "proxy/static", "provider-required", "missing-key", "unavailable"}
    return {
        "command": definition["command"],
        "label": definition["label"],
        "available": bool(available),
        "result_status": result_status,
        "source_status": command["source_status"],
        "fetched_at": provider_requirement.get("fetched_at"),
        "provider": provider_requirement.get("provider") or "none",
        "caveat": definition["caveat"],
        "data_gap": definition["data_gap"] if not available else provider_requirement.get("caveat") or definition["data_gap"],
        "provider_requirement": provider_requirement,
        "route": definition["route"],
        "workspace_view": definition["workspace_view"],
        "preview": {
            "title": definition["label"],
            "status": result_status,
            "message": _result_message(definition, result_status, provider_requirement),
            "source": provider_requirement.get("source") or "phase3_command_workspace",
            "caveat": definition["caveat"],
            "data_gap": definition["data_gap"] if not available else provider_requirement.get("caveat") or definition["caveat"],
        },
        "action_contract": {
            "action_type": "open_workstation_context",
            "enabled": bool(enabled),
            "broker_execution": False,
            "market_action_routing": False,
            "auth_required": False,
            "billing_required": False,
            "hosted_persistence": False,
            "non_advisory": True,
        },
        "allowed_actions": [
            {
                "action": "open_workspace_view",
                "enabled": bool(enabled),
                "target": definition["workspace_view"],
                "status": result_status,
                "caveat": RESEARCH_ONLY_NOTICE,
            },
            {
                "action": "inspect_provider_gap",
                "enabled": True,
                "target": definition["provider_family"],
                "status": result_status,
                "provider_status": provider_requirement.get("status"),
                "caveat": provider_requirement.get("recommended_action"),
            },
        ],
        "not_financial_advice": True,
    }


def _result_message(definition: dict[str, Any], result_status: str, provider_requirement: dict[str, Any]) -> str:
    command = definition["command"]
    if result_status == "available":
        return f"{command} can open a source-labeled workstation preview from {provider_requirement.get('provider')} evidence."
    if result_status == "source-backed-preview":
        return f"{command} has source-backed event context, but live-provider availability is not claimed."
    if result_status == "proxy/static":
        return f"{command} can open proxy/static context only; live layer coverage is not claimed."
    return f"{command} is schema-ready but unavailable until {definition['provider_family']} provider evidence is fresh or cached."


def _build_provider_requirements(
    definitions: list[dict[str, Any]],
    provider_requirements_by_command: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for definition in definitions:
        requirement = provider_requirements_by_command[definition["command"]]
        rows.append(
            {
                "command": definition["command"],
                "provider_family": definition["provider_family"],
                "provider": requirement.get("provider"),
                "status": requirement.get("status"),
                "fetched_at": requirement.get("fetched_at"),
                "requires_provider": bool(definition.get("requires_provider")),
                "available_for_live_result": requirement.get("status") in AVAILABLE_PROVIDER_STATUSES,
                "recommended_action": requirement.get("recommended_action"),
                "caveat": requirement.get("caveat"),
            }
        )
    return rows


def _history_seed(command_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for result in command_results[:8]:
        rows.append(
            {
                "raw": result["command"],
                "command": result["command"],
                "status": result["result_status"],
                "provider": result["provider"],
                "fixture_safe": True,
                "not_financial_advice": True,
            }
        )
    return rows


def _readiness() -> dict[str, Any]:
    unavailable = [
        {
            "capability": "broker_execution",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Keep commands read-only research routes; add no market-action pathway in Phase 3.",
            "caveat": "Phase 3 workstation actions are inspection and routing actions only.",
        },
        {
            "capability": "market_action_routing",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Do not add order placement or market-action routing.",
            "caveat": "Commands never place, approve, or route orders.",
        },
        {
            "capability": "hosted_persistence",
            "status": "unavailable",
            "source_status": "unavailable",
            "provider": "none",
            "recommended_action": "Review auth, retention, and storage contracts in a later commercial slice.",
            "caveat": "No hosted database, account system, auth, billing, or user-specific command state is added.",
        },
    ]
    return {
        "command_execution_mode": "read-only-workstation-actions",
        "broker_execution_added": False,
        "market_action_routing_added": False,
        "auth_added": False,
        "billing_added": False,
        "hosted_persistence_added": False,
        "graph_database_dependency_added": False,
        "paid_provider_dependency_added": False,
        "unavailable_capabilities": unavailable,
    }


def build_command_workspace_contract(
    *,
    event_graph: dict[str, Any] | None = None,
    provider_rows: Any = None,
) -> dict[str, Any]:
    """Build a deterministic command workspace contract from graph suggestions and provider status."""
    graph = event_graph or build_event_asset_graph_contract(provider_rows=provider_rows)
    contexts = _command_suggestion_contexts(graph)
    providers = _dedupe_rows([*_records(provider_rows), *_provider_rows_from_graph(graph)])
    provider_requirements_by_command: dict[str, dict[str, Any]] = {}
    commands: list[dict[str, Any]] = []
    command_results: list[dict[str, Any]] = []

    for definition in COMMAND_DEFINITIONS:
        requirement = _select_provider_requirement(definition, providers)
        provider_requirements_by_command[definition["command"]] = requirement
        result_status, available, source_status = _status_for_command(
            definition,
            requirement,
            has_context=_command_has_context(definition["command"], contexts),
        )
        command = _build_command_record(definition, result_status, source_status, requirement)
        result = _build_command_result(
            definition,
            command,
            requirement,
            available=available,
            result_status=result_status,
        )
        commands.append(command)
        command_results.append(result)

    provider_requirements = _build_provider_requirements(COMMAND_DEFINITIONS, provider_requirements_by_command)
    readiness = _readiness()
    available_count = sum(1 for result in command_results if result["available"])
    provider_required_count = sum(1 for result in command_results if result["result_status"] in {"provider-required", "missing-key", "unavailable"})
    return {
        "command_workspace_version": COMMAND_WORKSPACE_VERSION,
        "commands": commands,
        "contexts": contexts,
        "command_results": command_results,
        "history_seed": _history_seed(command_results),
        "provider_requirements": provider_requirements,
        "readiness": readiness,
        "evidence_refs": [*PHASE3_EVIDENCE_REFS, *EVENT_GRAPH_EVIDENCE_REFS],
        "summary": {
            "command_count": len(commands),
            "context_count": len(contexts),
            "command_result_count": len(command_results),
            "available_command_count": available_count,
            "provider_required_command_count": provider_required_count,
            "phase2f_command_suggestion_count": len(_records(graph.get("command_suggestions"))),
            "non_advisory": True,
            "broker_execution_added": False,
            "market_action_routing_added": False,
            "hosted_persistence_added": False,
            "paid_provider_dependency_added": False,
        },
    }
