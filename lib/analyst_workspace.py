from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import quote, urlencode, urlparse

from .symbol_intelligence import (
    SYMBOL_DELIVERY_VERSION,
    build_symbol_delivery_contract,
)


ANALYST_WORKSPACE_VERSION = "analyst_workspace.v1"
PANEL_IDS = (
    "chart-core",
    "technicals",
    "financials",
    "catalysts",
    "news",
    "sources",
    "comparison",
)
LAYOUT_PRESETS = ("research", "chart-focus", "events-evidence")
_SAFE_VALUE = re.compile(r"^[A-Za-z0-9_.:/,+ -]{1,160}$")
_SAFE_ORIGIN_STATE = re.compile(r"^[A-Za-z0-9_.%=&+-]{1,160}$")
_RETURN_KEYS = (
    "origin",
    "originState",
    "list",
    "type",
    "severity",
    "status",
    "change",
    "layout",
    "panel",
    "symbol",
    "interval",
    "range",
)


def _text(value: Any, default: str = "") -> str:
    current = str(value or "").strip()
    return current or default


def _safe_http_url(value: Any) -> str | None:
    current = _text(value)
    if not current:
        return None
    try:
        parsed = urlparse(current)
    except ValueError:
        return None
    return current if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _cache_identity(
    symbol: str,
    panel: str,
    interval: str,
    range_name: str,
    compare: str | None,
) -> str:
    parts = [
        "symbol-panel",
        symbol,
        panel,
        interval,
        range_name,
        compare or "none",
        SYMBOL_DELIVERY_VERSION,
    ]
    return ":".join(parts)


def _etag_identity(cache_identity: str) -> str:
    return hashlib.sha256(cache_identity.encode("utf-8")).hexdigest()[:20]


def map_change_type_to_panel(change_type: Any) -> str:
    normalized = _text(change_type).lower()
    if normalized in {"event", "news", "exact-news"}:
        return "catalysts"
    if normalized == "fundamental":
        return "financials"
    if normalized == "source-status":
        return "sources"
    return "chart-core"


def normalize_workspace_layout(value: Any = None) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    preset = _text(source.get("preset"), "research")
    if preset not in LAYOUT_PRESETS:
        preset = "research"
    try:
        split_percent = int(float(source.get("split_percent", 58)))
    except (TypeError, ValueError):
        split_percent = 58
    split_percent = min(72, max(36, split_percent))

    def panel_list(key: str, fallback: tuple[str, ...]) -> list[str]:
        raw = source.get(key)
        candidates = raw if isinstance(raw, (list, tuple)) else fallback
        result: list[str] = []
        for item in candidates:
            panel = _text(item).lower()
            if panel in PANEL_IDS and panel not in result:
                result.append(panel)
        return result or list(fallback)

    order = panel_list("panel_order", PANEL_IDS)
    visible = panel_list(
        "visible_panels",
        ("chart-core", "financials", "catalysts", "sources"),
    )
    focused = _text(source.get("focused_panel"), "chart-core").lower()
    if focused not in PANEL_IDS:
        focused = "chart-core"
    return {
        "preset": preset,
        "split_percent": split_percent,
        "panel_order": order,
        "visible_panels": visible,
        "focused_panel": focused,
    }


def sanitize_workspace_return_state(value: Any = None) -> dict[str, str]:
    source = value if isinstance(value, dict) else {}
    result: dict[str, str] = {}
    for key in _RETURN_KEYS:
        current = _text(source.get(key))
        if key == "originState":
            if result.get("origin") == "attention-desk" and _SAFE_ORIGIN_STATE.fullmatch(current):
                result[key] = current
            continue
        if not current or not _SAFE_VALUE.fullmatch(current):
            continue
        lowered = current.lower()
        if (
            lowered.startswith(("javascript:", "data:", "file:"))
            or "\\" in current
            or ".." in current
        ):
            continue
        result[key] = current
    return result


def _change_context(
    change: Any,
    *,
    symbol: str,
) -> tuple[dict[str, Any], str | None]:
    if not isinstance(change, dict) or not change:
        return {
            "status": "not-selected",
            "change_id": None,
            "symbol": symbol,
            "change_type": None,
            "focused_panel": None,
            "before": None,
            "after": None,
            "source_url": None,
            "caveat": "No saved Change Inbox event was selected.",
            "data_gap": None,
        }, None
    change_symbol = _text(change.get("symbol")).upper()
    if change_symbol != symbol:
        return {
            "status": "incompatible",
            "change_id": None,
            "symbol": symbol,
            "change_type": None,
            "focused_panel": None,
            "before": None,
            "after": None,
            "source_url": None,
            "caveat": "The selected change belongs to another symbol and was not attached.",
            "data_gap": "Open the exact saved change for this workspace symbol.",
        }, None
    change_type = _text(change.get("change_type"), "unknown").lower()
    focused = map_change_type_to_panel(change_type)
    return {
        "status": "exact",
        "change_id": _text(change.get("change_id")) or None,
        "symbol": symbol,
        "change_type": change_type,
        "field": _text(change.get("field")) or None,
        "severity": _text(change.get("severity")) or None,
        "before": change.get("before"),
        "after": change.get("after"),
        "observation": _text(change.get("observation")) or None,
        "focused_panel": focused,
        "source_url": _safe_http_url(change.get("source_url")),
        "caveat": "Saved before/after evidence is descriptive and is not a causal or directional claim.",
        "data_gap": None,
    }, focused


def _panel_manifest(
    workstation: dict[str, Any],
    *,
    symbol: str,
    asset_class: str,
    interval: str,
    range_name: str,
    compare: str | None,
) -> list[dict[str, Any]]:
    summary = workstation.get("summary") or {}
    clock = workstation.get("market_clock") or {}
    fetched_at = summary.get("fetched_at") or clock.get("fetched_at")
    primary_status = _text(summary.get("source_status"), "unavailable")
    metadata = {
        "chart-core": (
            "Price chart",
            True,
            primary_status,
            "Exact OHLCV chart data loads on demand.",
            None,
        ),
        "technicals": (
            "Technical evidence",
            True,
            "not-loaded",
            "Project-native indicators are calculated from exact displayed history.",
            "Technical rows have not been requested.",
        ),
        "financials": (
            "Financials",
            False,
            "not-loaded",
            "Provider-backed metrics and SEC facts load only for the exact symbol.",
            "Financial rows have not been requested.",
        ),
        "catalysts": (
            "Catalysts",
            False,
            "not-loaded",
            "Saved exact-symbol earnings, dividends, and news evidence loads on demand.",
            "A completed Research Snapshot may be required.",
        ),
        "news": (
            "Exact news",
            False,
            "not-loaded",
            "Only exact symbol/name matches are eligible.",
            "Exact news rows have not been requested.",
        ),
        "sources": (
            "Sources",
            False,
            primary_status,
            "Source, freshness, caveat, and data-gap evidence for this symbol.",
            None,
        ),
        "comparison": (
            "Comparison",
            True,
            "not-loaded",
            "Comparison requires a second verified compatible history.",
            None if compare else "No comparison symbol is selected.",
        ),
    }
    panels: list[dict[str, Any]] = []
    for panel_id in PANEL_IDS:
        title, timeframe_linked, source_status, caveat, data_gap = metadata[panel_id]
        applicable = not (
            panel_id == "financials" and asset_class == "crypto"
        )
        if not applicable:
            source_status = "not_applicable"
            data_gap = "Conventional issuer financial statements do not apply to this crypto pair."
        cache_identity = _cache_identity(
            symbol,
            panel_id,
            interval if timeframe_linked else "identity",
            range_name if timeframe_linked else "identity",
            compare if panel_id == "comparison" else None,
        )
        panels.append(
            {
                "panel_id": panel_id,
                "title": title,
                "symbol": symbol,
                "compatibility": "compatible" if applicable else "not_applicable",
                "delivery_status": "ready-reference" if panel_id == "sources" else "on-demand",
                "endpoint": (
                    f"/api/symbol-workstation/{quote(symbol, safe='')}/panels/"
                    f"{quote(panel_id, safe='')}"
                ),
                "request_params": {
                    "asset_class": asset_class,
                    "interval": interval,
                    "range": range_name,
                    "compare": compare,
                },
                "cache_identity": cache_identity,
                "etag_identity": _etag_identity(cache_identity),
                "timeframe_linked": timeframe_linked,
                "desktop_default_visible": panel_id
                in {"chart-core", "financials", "catalysts", "sources"},
                "mobile_lazy": panel_id != "chart-core",
                "provider": summary.get("provider") if panel_id in {"chart-core", "sources"} else "on-demand-panel",
                "source_url": _safe_http_url(workstation.get("quote", {}).get("source_url")),
                "source_status": source_status,
                "fetched_at": fetched_at if panel_id in {"chart-core", "sources"} else None,
                "confidence": 0.4 if source_status == "fixture" else None,
                "caveat": caveat,
                "data_gap": data_gap,
                "not_financial_advice": True,
            }
        )
    return panels


def _unknown_workspace(
    symbol: str,
    *,
    asset_class: str | None,
    interval: str,
    range_name: str,
    return_state: dict[str, str],
) -> dict[str, Any]:
    return {
        "workspace_version": ANALYST_WORKSPACE_VERSION,
        "identity": {
            "symbol": symbol,
            "name": None,
            "asset_class": asset_class,
            "compatibility": "unknown",
            "caveat": "No exact identity is present in the bounded symbol registry.",
            "data_gap": "Unknown symbols are never substituted with fixture data.",
        },
        "context": {
            "symbol": symbol,
            "asset_class": asset_class,
            "interval": interval,
            "range": range_name,
            "focused_panel": "chart-core",
            "layout_preset": "research",
            "return_state": return_state,
        },
        "quote": {},
        "panels": [],
        "layouts": normalize_workspace_layout(),
        "change_context": {
            "status": "unavailable",
            "change_id": None,
            "data_gap": "The workspace identity is unavailable.",
        },
        "actions": [],
        "request_plan": {
            "initial_heavy_panel_count": 0,
            "desktop_maximum_panel_requests": 0,
            "mobile_initial_panel_requests": 0,
            "hidden_mobile_panels_eagerly_fetched": False,
            "concurrent_request_deduplication_required": True,
            "same_symbol_lkg_required": True,
            "broad_universe_fanout": False,
            "watchlist_refresh_provider_call_ceiling": 16,
        },
        "source_register": [],
        "readiness": {
            "status": "unavailable",
            "exact_identity": False,
            "progressive_delivery": True,
        },
        "evidence_refs": [],
        "summary": {
            "workspace": "analyst-workspace",
            "workspace_count": 0,
            "symbol": symbol,
            "status": "unavailable",
        },
        "not_financial_advice": True,
    }


def build_analyst_workspace_contract(
    symbol: str,
    *,
    asset_class: str | None = None,
    interval: str = "1d",
    range_name: str = "3mo",
    runtime_mode: str = "cache",
    compare: str | None = None,
    layout: Any = None,
    return_state: Any = None,
    change_context: Any = None,
) -> dict[str, Any]:
    requested_symbol = _text(symbol).upper()
    safe_return = sanitize_workspace_return_state(return_state)
    summary_contract = build_symbol_delivery_contract(
        requested_symbol,
        asset_class=asset_class,
        interval=interval,
        range_name=range_name,
        runtime_mode=runtime_mode,
        delivery="summary",
        compare=compare,
    )
    workstations = summary_contract.get("workstations") or []
    if not workstations:
        return _unknown_workspace(
            requested_symbol,
            asset_class=asset_class,
            interval=interval,
            range_name=range_name,
            return_state=safe_return,
        )

    workstation = workstations[0]
    identity = dict(workstation.get("identity") or {})
    exact_symbol = _text(identity.get("symbol")).upper()
    if exact_symbol != requested_symbol:
        return _unknown_workspace(
            requested_symbol,
            asset_class=asset_class,
            interval=interval,
            range_name=range_name,
            return_state=safe_return,
        )
    resolved_asset_class = _text(identity.get("asset_class"), asset_class or "unknown")
    normalized_layout = normalize_workspace_layout(layout)
    selected_change, mapped_panel = _change_context(
        change_context,
        symbol=exact_symbol,
    )
    focused_panel = mapped_panel or normalized_layout["focused_panel"]
    normalized_layout["focused_panel"] = focused_panel
    quote_row = workstation.get("quote") or {}
    clock = workstation.get("market_clock") or {}
    source_register = [
        {
            "provider": row.get("provider"),
            "source": row.get("source"),
            "source_url": _safe_http_url(row.get("source_url")),
            "source_status": row.get("source_status"),
            "fetched_at": row.get("fetched_at"),
            "confidence": row.get("confidence"),
            "caveat": row.get("caveat"),
            "data_gap": row.get("data_gap"),
        }
        for row in (workstation.get("source_register") or [])[:6]
        if isinstance(row, dict)
    ]
    panels = _panel_manifest(
        workstation,
        symbol=exact_symbol,
        asset_class=resolved_asset_class,
        interval=interval,
        range_name=range_name,
        compare=compare,
    )
    query = {
        "view": "asset",
        "symbol": exact_symbol,
        "asset": resolved_asset_class,
        "interval": interval,
        "range": range_name,
    }
    actions = [
        {
            "action_id": "open-single-panel",
            "label": "Open single-panel asset view",
            "kind": "internal-navigation",
            "href": f"/?{urlencode(query)}",
            "verified": True,
        },
        {
            "action_id": "open-command-workspace",
            "label": "Open command workspace",
            "kind": "internal-navigation",
            "href": f"/?{urlencode({'view': 'command-workspace', 'symbol': exact_symbol})}",
            "verified": True,
        },
    ]
    source_url = _safe_http_url(quote_row.get("source_url"))
    if source_url:
        actions.append(
            {
                "action_id": "open-primary-source",
                "label": "Open primary source",
                "kind": "external-source",
                "href": source_url,
                "verified": True,
            }
        )
    return {
        "workspace_version": ANALYST_WORKSPACE_VERSION,
        "identity": {
            "symbol": exact_symbol,
            "name": identity.get("name"),
            "asset_class": resolved_asset_class,
            "exchange": identity.get("exchange"),
            "currency": identity.get("currency"),
            "sector": identity.get("sector"),
            "industry": identity.get("industry"),
            "compatibility": "exact",
            "source_status": identity.get("source_status"),
            "caveat": identity.get("caveat"),
            "data_gap": identity.get("data_gap"),
        },
        "context": {
            "symbol": exact_symbol,
            "asset_class": resolved_asset_class,
            "interval": interval,
            "range": range_name,
            "compare": compare,
            "focused_panel": focused_panel,
            "layout_preset": normalized_layout["preset"],
            "quote_clock": quote_row.get("fetched_at"),
            "market_clock": clock.get("market_data_as_of"),
            "source_clock": clock.get("retrieved_at") or quote_row.get("fetched_at"),
            "market_data_status": clock.get("market_data_status"),
            "return_state": safe_return,
        },
        "quote": {
            "last_price": quote_row.get("last_price"),
            "change": quote_row.get("change"),
            "change_pct": quote_row.get("change_pct"),
            "currency": quote_row.get("currency"),
            "provider": quote_row.get("provider"),
            "source_url": source_url,
            "source_status": quote_row.get("source_status"),
            "fetched_at": quote_row.get("fetched_at"),
            "caveat": quote_row.get("caveat"),
            "data_gap": quote_row.get("data_gap"),
        },
        "panels": panels,
        "layouts": {
            **normalized_layout,
            "available_presets": list(LAYOUT_PRESETS),
            "split_bounds": {"minimum": 36, "maximum": 72},
            "persistence": "local-only",
            "storage_key": "global-terminal.analyst-layout.v1",
            "hosted_sync": False,
            "private_fields_allowed": False,
        },
        "change_context": selected_change,
        "actions": actions,
        "request_plan": {
            "initial_contract": "summary-and-panel-references-only",
            "initial_heavy_panel_count": 0,
            "initial_saved_primary_panel_count": 1,
            "initial_document_useful_primary_panel": True,
            "desktop_default_panels": [
                "chart-core",
                "financials",
                "catalysts",
                "sources",
            ],
            "desktop_maximum_panel_requests": 4,
            "mobile_default_panel": focused_panel,
            "mobile_initial_panel_requests": 1,
            "hidden_mobile_panels_eagerly_fetched": False,
            "concurrent_request_deduplication_required": True,
            "etag_revalidation": True,
            "same_symbol_lkg_required": True,
            "broad_universe_fanout": False,
            "watchlist_refresh_provider_call_ceiling": 16,
            "workspace_composition_provider_calls": 0,
        },
        "source_register": source_register,
        "readiness": {
            "status": "ready",
            "exact_identity": True,
            "progressive_delivery": True,
            "layout_persistence": "local-only",
            "hosted_sync": False,
            "broker_execution": False,
            "autonomous_ai_action": False,
        },
        "evidence_refs": [
            "docs/PHASE_6H_WORKSPACE_CONTRACT.md",
            "docs/PHASE_6H_PREFLIGHT_AND_BOTTLENECKS.md",
        ],
        "summary": {
            "workspace": "analyst-workspace",
            "workspace_count": 1,
            "symbol": exact_symbol,
            "status": quote_row.get("source_status") or "available",
            "panel_count": len(panels),
            "focused_panel": focused_panel,
        },
        "not_financial_advice": True,
    }


def build_analyst_workspace_fixture_contract() -> dict[str, Any]:
    return build_analyst_workspace_contract(
        "AAPL",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        runtime_mode="fixture",
    )


def workspace_semantic_hash(workspace: dict[str, Any]) -> str:
    encoded = json.dumps(
        workspace,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
