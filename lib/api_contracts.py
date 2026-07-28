from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from .ai_providers import list_available_ai_providers, select_ai_provider
from .analyst_workspace import build_analyst_workspace_contract
from .attention_desk import build_attention_desk_contract
from .asset_universe import build_asset_universe_contract
from .command_workspace import build_command_workspace_contract
from .crypto_intelligence_contract import build_crypto_intelligence_contract
from .data_status import DataResult, get_recent_results
from .daily_briefing import (
    build_current_daily_brief_contract,
    build_daily_brief_history_contract,
    build_demo_daily_brief_contract,
)
from .equity_intelligence import build_equity_intelligence_contract
from .event_asset_graph import build_event_asset_graph_contract
from .feed_registry import build_feed_registry
from .identity_tenancy import build_account_workspace_contract
from .hosted_scheduler_operations import build_fixture_hosted_scheduler_contract
from .layer_registry import build_layer_runtime_payload
from .map_news_event_fusion import build_map_news_event_fusion_contract
from .market_intelligence import build_market_intelligence_contract
from .market_map_screener import build_market_map_screener_contract
from .news_intelligence import build_worldmonitor_style_news_dashboard
from .portfolio_risk_workstation import build_portfolio_risk_workstation_contract
from .product_parity_inventory import build_product_parity_inventory
from .provider_health_engine import build_provider_health_ledger, summarize_provider_health_ledger
from .research_report_workstation import build_research_report_workstation_contract, find_forbidden_report_phrases
from .research_operations import (
    ResearchOperationsStore,
    build_research_operations_contract,
)
from .research_memory import build_research_memory_contract
from .symbol_intelligence import (
    build_symbol_delivery_contract,
    build_symbol_intelligence_contract,
    build_symbol_intelligence_fixture_catalog,
)
from .symbol_workstation import build_symbol_directory_contract
from .watchlist_desk import (
    build_watchlist_change_contract,
    build_watchlist_desk_contract,
    build_watchlist_desk_fixture_contract,
)
from .watchlist_alert_manager import build_watchlist_alert_manager_fixture_contract
from .war_room_map import build_war_room_map_contract
from .war_room_map_replay import build_demo_war_room_map_replay_contract, build_war_room_map_replay_contract
from .web_market_workstations import (
    build_financial_fundamentals_contract,
    build_options_quant_contract,
    build_screener_drilldown_contract,
)

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


API_CONTRACT_VERSION = "phase_2b.v1"

PROVENANCE_FIELDS = [
    "provider",
    "source",
    "source_url",
    "fetched_at",
    "freshness",
    "source_status",
    "confidence",
    "coordinate_method",
    "data_gap",
    "caveat",
]

SECRET_FIELD_NAMES = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "password",
    "secret",
    "token",
}

LIVE_STATUS_VALUES = {"live/fresh"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _field_is_secret(name: Any) -> bool:
    normalized = str(name or "").strip().lower()
    return normalized in SECRET_FIELD_NAMES or normalized.endswith("_secret") or normalized.endswith("_token")


def _redacted(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    return "[redacted]"


def to_json_safe(value: Any) -> Any:
    """Convert runtime objects into JSON-safe primitives for API boundaries."""
    if isinstance(value, DataResult):
        return to_json_safe(value.to_dict())
    if is_dataclass(value) and not isinstance(value, type):
        return to_json_safe(asdict(value))
    if pd is not None:
        if isinstance(value, pd.DataFrame):
            return [to_json_safe(row) for row in value.to_dict(orient="records")]
        if isinstance(value, pd.Series):
            return to_json_safe(value.to_dict())
        if isinstance(value, pd.Timestamp):
            if pd.isna(value):
                return None
            return value.isoformat()
        if value is pd.NaT:
            return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            output_key = str(key)
            safe[output_key] = _redacted(item) if _field_is_secret(output_key) else to_json_safe(item)
        return safe
    if isinstance(value, (list, tuple, set)):
        return [to_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return to_json_safe(value.item())
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            return to_json_safe(value.to_dict())
        except Exception:
            pass
    return str(value)


def _records(value: Any, *, limit: int | None = None) -> list[dict[str, Any]]:
    safe = to_json_safe(value)
    if safe is None:
        rows: list[dict[str, Any]] = []
    elif isinstance(safe, list):
        rows = [dict(item) for item in safe if isinstance(item, dict)]
    elif isinstance(safe, dict):
        rows = [dict(safe)]
    else:
        rows = []
    return rows[:limit] if limit is not None else rows


def _status_records(statuses: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    return _records(list(statuses or []))


def _dataframe_like(value: Any) -> bool:
    return pd is not None and isinstance(value, (pd.DataFrame, pd.Series, pd.Timestamp))


def _envelope(
    payload_type: str,
    data: Any,
    *,
    summary: dict[str, Any] | None = None,
    source_status: Iterable[Any] | None = None,
    unavailable: Iterable[Any] | None = None,
    errors: Iterable[Any] | None = None,
    caveats: Iterable[str] | None = None,
) -> dict[str, Any]:
    return {
        "contract_version": API_CONTRACT_VERSION,
        "payload_type": payload_type,
        "generated_at": _now_iso(),
        "data": to_json_safe(data),
        "summary": to_json_safe(summary or {}),
        "source_status": to_json_safe(list(source_status or [])),
        "unavailable": to_json_safe(list(unavailable or [])),
        "errors": to_json_safe(list(errors or [])),
        "caveats": [str(item) for item in caveats or [] if str(item)],
    }


@dataclass(frozen=True)
class ApiRouteDescriptor:
    method: str
    path: str
    payload_type: str
    description: str
    live_fetch_default: bool = False
    requires_fastapi: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return to_json_safe(asdict(self))


API_ROUTE_DESCRIPTORS = [
    ApiRouteDescriptor("GET", "/api/product-parity", "product_parity_inventory", "Streamlit-to-web parity inventory and migration queue."),
    ApiRouteDescriptor("GET", "/api/attention-desk", "attention_desk", "Compose a zero-provider-call daily attention queue from stored source evidence."),
    ApiRouteDescriptor("GET", "/api/market-intelligence", "market_intelligence", "Cross-asset market overview with source-labeled chart specs."),
    ApiRouteDescriptor("GET", "/api/equity-intelligence", "equity_intelligence", "Equity, fundamentals, options-readiness, scenarios, and chart specs."),
    ApiRouteDescriptor("GET", "/api/financial-fundamentals", "financial_fundamentals", "Dedicated financial profile, metrics, valuation quality, and source register."),
    ApiRouteDescriptor("GET", "/api/options-quant", "options_quant", "Provider-backed option chain, quality, implied volatility, Greeks, exposure assumptions, and scenarios."),
    ApiRouteDescriptor("GET", "/api/portfolio-risk", "portfolio_risk", "Privacy-safe valuation, performance, drawdown, risk, correlation, factor, attribution, and stress research."),
    ApiRouteDescriptor("GET", "/api/screener-drilldown", "screener_drilldown", "Heatmap tile drilldown targets, sector summaries, and provider-gated screener state."),
    ApiRouteDescriptor("GET", "/api/market-map-screener", "market_map_screener", "Provider-backed market heatmap, ranked screener rows, sectors, and risk versus return comparison."),
    ApiRouteDescriptor("GET", "/api/market-map-snapshot", "market_map_screener", "Read-optimized materialized Market Map snapshot with conditional HTTP caching."),
    ApiRouteDescriptor("GET", "/api/market-map-snapshot/{symbol}", "market_snapshot_detail", "Exact-symbol detail from the materialized Market Map snapshot."),
    ApiRouteDescriptor("GET", "/api/market-refresh-health", "market_refresh_health", "Local materialization refresh status, duration, row count, last success, and stale/error state."),
    ApiRouteDescriptor("GET", "/api/market-refresh-history", "market_refresh_history", "Bounded local operational history for materialized Market Map refresh jobs."),
    ApiRouteDescriptor("GET", "/api/market-map-screens", "saved_market_screens", "Local-private saved market screen definitions and readiness."),
    ApiRouteDescriptor("POST", "/api/market-map-screens", "saved_market_screen", "Create a validated local-private market screen from a request body."),
    ApiRouteDescriptor("PATCH", "/api/market-map-screens/{screen_id}", "saved_market_screen", "Rename a local-private saved market screen."),
    ApiRouteDescriptor("DELETE", "/api/market-map-screens/{screen_id}", "saved_market_screen_archive", "Archive a local-private saved market screen."),
    ApiRouteDescriptor("GET", "/api/crypto-intelligence", "crypto_intelligence", "Crypto market, derivatives, scenarios, and chart specs."),
    ApiRouteDescriptor("GET", "/api/symbol-directory", "symbol_directory", "Bounded source-labeled equity, ETF, and crypto identity search."),
    ApiRouteDescriptor("GET", "/api/symbol-workstation", "symbol_workstation", "Universal source-aware symbol OHLCV, technical, financial/news, comparison, and asset-specific context."),
    ApiRouteDescriptor("GET", "/api/symbol-workstation/{symbol}", "symbol_workstation", "Exact materialized-identity workstation with symbol-scoped cache/LKG and conditional HTTP caching."),
    ApiRouteDescriptor("GET", "/api/symbol-workstation/{symbol}/summary", "symbol_workstation", "Compact exact identity/quote summary with no provider refresh."),
    ApiRouteDescriptor("GET", "/api/symbol-workstation/{symbol}/panels/{panel}", "symbol_workstation", "Exact compact chart-core, technicals, financials, news, sources, or comparison panel delivered on demand."),
    ApiRouteDescriptor("GET", "/api/analyst-workspace/{symbol}", "analyst_workspace", "Compact synchronized exact-symbol workspace manifest with progressive panel references and local-only layout state."),
    ApiRouteDescriptor("GET", "/api/analyst-workspace/{symbol}/operations", "research_operations", "Exact-symbol panel freshness SLO, observed provider health, bounded queue, LKG, and retry truth."),
    ApiRouteDescriptor("POST", "/api/analyst-workspace/{symbol}/refresh", "research_refresh_job", "Queue one bounded exact-symbol refresh with a precomputed provider-call ceiling."),
    ApiRouteDescriptor("GET", "/api/research-operations/jobs/{job_id}", "research_refresh_job", "Read one bounded process-local exact research refresh job."),
    ApiRouteDescriptor("GET", "/api/account/session", "account_workspace", "Anonymous/local or process-local test identity, tenant, entitlement, and persistence truth."),
    ApiRouteDescriptor("POST", "/api/account/hosted-session", "account_workspace", "Create an explicitly enabled Supabase password session behind opaque HttpOnly and CSRF cookies, then restore the server-derived tenant workspace."),
    ApiRouteDescriptor("POST", "/api/account/local-session", "account_workspace", "Create an explicitly enabled process-local test session; never hosted auth."),
    ApiRouteDescriptor("POST", "/api/account/signout", "account_workspace", "Revoke the current hosted or process-local session and return to local mode."),
    ApiRouteDescriptor("GET", "/api/account/preferences/{key}", "account_preference", "Read one server-tenant-scoped workspace preference."),
    ApiRouteDescriptor("PUT", "/api/account/preferences/{key}", "account_preference", "Save one CSRF-protected, versioned, tenant-scoped preference."),
    ApiRouteDescriptor("DELETE", "/api/account/preferences/{key}", "account_preference", "Delete one CSRF-protected, versioned, tenant-scoped preference."),
    ApiRouteDescriptor("GET", "/api/account/export", "account_export", "Bounded export of preferences owned by the current tenant."),
    ApiRouteDescriptor("GET", "/api/account/continuity", "account_continuity_status", "Read hosted repository, pending recovery, conflict, and last-known-good continuity truth for the current server-derived tenant."),
    ApiRouteDescriptor("POST", "/api/account/continuity/replay", "account_continuity_replay", "Replay a bounded current-tenant offline queue through the verified user JWT and optimistic repository version."),
    ApiRouteDescriptor("POST", "/api/account/continuity/resolve", "account_continuity_resolution", "Explicitly resolve one local/hosted divergence by keeping local or restoring hosted state."),
    ApiRouteDescriptor("GET", "/api/account/continuity/export", "account_continuity_export", "Export a bounded credential-free, identity-free current-tenant account bundle."),
    ApiRouteDescriptor("POST", "/api/account/continuity/import", "account_continuity_import", "Validate and explicitly merge or replace one bounded account backup into the current server-derived tenant, then reconcile hosted state."),
    ApiRouteDescriptor("DELETE", "/api/account/continuity", "account_continuity_delete", "Soft-delete the hosted account document with optimistic versioning while retaining local state and immutable audit evidence."),
    ApiRouteDescriptor("GET", "/api/account/research-desk", "tenant_research_desk", "Read the current session tenant's account-owned watchlists, rules, and in-app inbox."),
    ApiRouteDescriptor("GET", "/api/account/research-desk/imports/preview", "tenant_research_import_preview", "Bounded read-only preview of a local saved watchlist; no provider call or private note copy."),
    ApiRouteDescriptor("POST", "/api/account/research-desk/imports", "tenant_research_import", "Explicitly consent to an idempotent, CSRF-protected account watchlist import."),
    ApiRouteDescriptor("GET", "/api/account/research-desk/watchlists/{resource_id}", "tenant_research_watchlist", "Read one session-tenant-owned account watchlist."),
    ApiRouteDescriptor("DELETE", "/api/account/research-desk/watchlists/{resource_id}", "tenant_research_watchlist", "Delete one versioned account watchlist and its tenant-owned children."),
    ApiRouteDescriptor("PUT", "/api/account/research-desk/watchlists/{resource_id}/rule", "tenant_research_rule", "Configure an opt-in versioned in-app saved-change rule."),
    ApiRouteDescriptor("POST", "/api/account/research-desk/watchlists/{resource_id}/inbox", "tenant_research_scan", "Evaluate saved local observations without provider calls and store deduplicated tenant inbox rows."),
    ApiRouteDescriptor("GET", "/api/account/research-desk/inbox/{resource_id}", "tenant_research_inbox_item", "Read one session-tenant-owned in-app research item."),
    ApiRouteDescriptor("PATCH", "/api/account/research-desk/inbox/{resource_id}", "tenant_research_inbox_item", "Review or acknowledge one versioned in-app research item."),
    ApiRouteDescriptor("GET", "/api/account/research-desk/export", "tenant_research_export", "Bounded tenant-owned account research export without local private notes or secrets."),
    ApiRouteDescriptor("GET", "/api/account/research-desk/sync", "tenant_research_sync_status", "Read the tenant-qualified local queue and hosted-verification truth state."),
    ApiRouteDescriptor("GET", "/api/account/research-desk/sync/preview", "tenant_research_sync_preview", "Preview a bounded private-field-free reconciliation plan without automatic upload."),
    ApiRouteDescriptor("POST", "/api/account/research-desk/sync/queue", "tenant_research_sync_mutation", "Explicitly consent to queue one bounded idempotent account research snapshot."),
    ApiRouteDescriptor("POST", "/api/account/research-desk/sync/replay", "tenant_research_sync_replay", "Replay bounded queued mutations only when a hosted adapter has passed verification."),
    ApiRouteDescriptor("DELETE", "/api/account/research-desk/sync/queue/{mutation_id}", "tenant_research_sync_mutation", "Cancel one current-tenant pending, retrying, or conflicting sync mutation."),
    ApiRouteDescriptor("GET", "/api/account/attention-desk", "attention_desk", "Compose stored evidence with current-session private review state and policy."),
    ApiRouteDescriptor("GET", "/api/account/observation-runs", "observation_runs", "Read current-tenant saved-Watchlist observation runs without provider calls."),
    ApiRouteDescriptor("POST", "/api/account/observation-runs", "observation_run", "Explicitly start one bounded, quota-aware saved-Watchlist observation run."),
    ApiRouteDescriptor("GET", "/api/account/observation-runs/{run_id}", "observation_run", "Read one current-tenant observation run and its source clocks."),
    ApiRouteDescriptor("POST", "/api/account/observation-runs/{run_id}/cancel", "observation_run", "Request cancellation for one current-tenant observation run."),
    ApiRouteDescriptor("GET", "/api/account/alert-manager", "watchlist_alert_manager", "Read tenant-owned alert rules, due state, stored-observation evaluations, and in-app trigger history with zero provider calls."),
    ApiRouteDescriptor("GET", "/api/account/alert-manager/scheduler", "hosted_scheduler_operations", "Read tenant-owned hosted schedule, run, quota, source, lease, and recovery truth with zero market-provider calls."),
    ApiRouteDescriptor("POST", "/api/account/alert-manager/scheduler/schedules", "hosted_scheduler_schedule", "Create one disabled bounded hosted schedule for an exact saved Watchlist and alert policy."),
    ApiRouteDescriptor("PATCH", "/api/account/alert-manager/scheduler/schedules/{schedule_id}", "hosted_scheduler_schedule", "Enable, pause, resume, kill, recover, retry, or delete one optimistic-versioned tenant schedule."),
    ApiRouteDescriptor("GET", "/api/account/alert-manager/scheduler/audit", "hosted_scheduler_audit", "Read bounded immutable scheduler control and run transition evidence for the current tenant."),
    ApiRouteDescriptor("POST", "/api/account/alert-manager/rules", "watchlist_alert_rule", "Create one bounded deterministic rule for an exact saved-Watchlist symbol."),
    ApiRouteDescriptor("PATCH", "/api/account/alert-manager/rules/{resource_id}", "watchlist_alert_rule", "Pause, resume, or cancel one optimistic-versioned tenant alert rule."),
    ApiRouteDescriptor("DELETE", "/api/account/alert-manager/rules/{resource_id}", "watchlist_alert_rule", "Soft-delete one tenant alert rule while retaining bounded audit evidence."),
    ApiRouteDescriptor("POST", "/api/account/alert-manager/evaluations", "watchlist_alert_evaluation", "Manually evaluate due rules from validated Phase 6N stored observations without market-provider calls."),
    ApiRouteDescriptor("PATCH", "/api/account/alert-manager/triggers/{trigger_id}", "watchlist_alert_trigger", "Review or acknowledge one optimistic-versioned in-app trigger."),
    ApiRouteDescriptor("GET", "/api/account/alert-manager/export", "watchlist_alert_export", "Export bounded tenant-owned alert rules, trigger history, runs, and audit without private fields."),
    ApiRouteDescriptor("PATCH", "/api/account/attention-desk/items/{fingerprint}", "attention_review_state", "Review, acknowledge, snooze, or undo snooze for one current-tenant attention fingerprint."),
    ApiRouteDescriptor("PUT", "/api/account/attention-desk/policy", "attention_policy", "Save one optimistic-versioned current-tenant in-app attention policy."),
    ApiRouteDescriptor("POST", "/api/account/attention-desk/checkpoint", "attention_checkpoint", "Advance the current-tenant review checkpoint without changing provider clocks."),
    ApiRouteDescriptor("GET", "/api/account/attention-desk/audit", "attention_audit", "Read bounded generic current-tenant Attention mutation audit rows."),
    ApiRouteDescriptor("GET", "/api/symbol-intelligence", "symbol_workstation", "Alias for the Phase 5N source-backed multi-panel symbol workstation."),
    ApiRouteDescriptor("GET", "/api/watchlist-desk", "watchlist_desk", "Local-private named watchlists, exact identities, delayed quote context, and bounded materialization health."),
    ApiRouteDescriptor("GET", "/api/watchlist-desk/lists/{list_id}/changes", "watchlist_desk", "Source-preserving diff between the latest two completed same-list Research Snapshots."),
    ApiRouteDescriptor("POST", "/api/watchlist-desk/lists", "watchlist_desk_action", "Create a named local-private watchlist."),
    ApiRouteDescriptor("PATCH", "/api/watchlist-desk/lists/{list_id}", "watchlist_desk_action", "Rename a named local-private watchlist."),
    ApiRouteDescriptor("POST", "/api/watchlist-desk/lists/{list_id}/items", "watchlist_desk_action", "Add an exact validated identity to a local-private watchlist."),
    ApiRouteDescriptor("PATCH", "/api/watchlist-desk/lists/{list_id}/order", "watchlist_desk_action", "Persist exact watchlist item order."),
    ApiRouteDescriptor("DELETE", "/api/watchlist-desk/lists/{list_id}/items/{item_id}", "watchlist_desk_action", "Archive one local-private watchlist item."),
    ApiRouteDescriptor("POST", "/api/watchlist-desk/lists/{list_id}/materialize", "watchlist_materialization", "Run a bounded manual selected-watchlist history materialization job."),
    ApiRouteDescriptor("POST", "/api/watchlist-desk/lists/{list_id}/change-alert-rule", "watchlist_change_alert_action", "Opt into a local preview-only watchlist change rule."),
    ApiRouteDescriptor("POST", "/api/watchlist-desk/lists/{list_id}/change-alert-previews", "watchlist_change_alert_action", "Persist deduplicated local preview events without external delivery."),
    ApiRouteDescriptor("PATCH", "/api/watchlist-desk/change-alert-events/{event_id}/acknowledge", "watchlist_change_alert_action", "Acknowledge one local preview event."),
    ApiRouteDescriptor("GET", "/api/feeds", "feed_registry", "Curated feed taxonomy and source caveats."),
    ApiRouteDescriptor("GET", "/api/runtime-health", "runtime_health", "Local Next/FastAPI/runtime orchestration health, launch guidance, and provider-route readiness."),
    ApiRouteDescriptor("GET", "/api/provider-health", "provider_health", "Recent provider health ledger."),
    ApiRouteDescriptor("GET", "/api/layers", "layer_runtime", "Map-layer runtime status and row counts."),
    ApiRouteDescriptor("GET", "/api/news", "news_dashboard", "News dashboard rows, impact matrix, freshness, and notes."),
    ApiRouteDescriptor("GET", "/api/war-room", "war_room", "War Room summary without Plotly/DataFrame objects."),
    ApiRouteDescriptor("GET", "/api/ai-providers", "ai_provider_status", "Free-first AI provider status without secret values."),
    ApiRouteDescriptor("GET", "/api/asset-universe", "asset_universe", "Reference-schema asset universe and command routing readiness."),
    ApiRouteDescriptor("GET", "/api/event-asset-graph", "event_asset_graph", "Clean-room event-to-asset graph contract with provenance and unavailable persistence."),
    ApiRouteDescriptor("GET", "/api/command-workspace", "command_workspace", "Provider-gated clean-room terminal actions from graph command suggestions."),
    ApiRouteDescriptor("GET", "/api/war-room-map", "war_room_map", "Map-first War Room contract with source-backed markers, layer gates, timeline filters, and compare readiness."),
    ApiRouteDescriptor("GET", "/api/map-news-event-fusion", "map_news_event_fusion", "Map-linked news, event graph, provider health, layer state, and heatmap context."),
    ApiRouteDescriptor("GET", "/api/war-room-map-snapshots", "war_room_map_replay", "Local-private project-captured War Map snapshot timeline."),
    ApiRouteDescriptor("POST", "/api/war-room-map-snapshots", "war_room_map_replay", "Capture the current server-built War Map fusion payload with append-only deduplication."),
    ApiRouteDescriptor("GET", "/api/war-room-map-replay", "war_room_map_replay", "Replay one captured War Map observation and optionally compare it with another."),
    ApiRouteDescriptor("GET", "/api/research-report", "research_report", "Source-bound non-advisory research report contract inspired by Gold Quant structure."),
    ApiRouteDescriptor("GET", "/api/research-memory", "research_memory", "Local-first research inbox, watchlists, reports, immutable source history, and sanitized export readiness."),
    ApiRouteDescriptor("GET", "/api/daily-brief", "daily_brief", "Source-bound deterministic daily briefing with captured-prior comparison."),
    ApiRouteDescriptor("GET", "/api/daily-brief/captures", "daily_brief_history", "Local-private append-only daily brief capture timeline."),
    ApiRouteDescriptor("POST", "/api/daily-brief/captures", "daily_brief_capture", "Capture the current server-composed daily brief with semantic deduplication."),
    ApiRouteDescriptor("PATCH", "/api/daily-brief/captures/{brief_id}/review", "daily_brief_capture", "Update local review state without placing private notes in URLs or fixtures."),
]


def _workspace_source_rows(workspace: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _records(workspace.get("provider_status"))
    if rows:
        return rows
    rows.extend(_records(workspace.get("source_status")))
    rows.extend(_records(workspace.get("streamlit_pages")))
    rows.extend(_records(workspace.get("lib_engines")))
    return rows


def _workspace_unavailable_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unavailable_statuses = {"missing-key", "provider-required", "unavailable", "forbidden/subscription-blocked"}
    return [
        row
        for row in rows
        if row.get("availability") == "unavailable"
        or str(row.get("status") or row.get("source_status") or "").lower() in unavailable_statuses
    ]


def _workspace_error_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("error")]


def build_api_product_parity_payload() -> dict[str, Any]:
    inventory = build_product_parity_inventory()
    source_rows = _workspace_source_rows(inventory)
    missing_rows = _records(inventory.get("missing_web_surfaces"))
    return _envelope(
        "product_parity_inventory",
        inventory,
        summary=inventory.get("summary") or {},
        source_status=source_rows,
        unavailable=missing_rows,
        caveats=[
            "Product parity inventory is source-backed from local repository files and does not imply runtime provider availability.",
            "External references are behavior evidence only unless a compatible license review allows direct use.",
        ],
    )


def build_api_attention_desk_payload(
    contract: dict[str, Any] | None = None,
    **contract_kwargs: Any,
) -> dict[str, Any]:
    desk = to_json_safe(contract or build_attention_desk_contract(**contract_kwargs))
    source_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in _records(desk.get("all_items")):
        for source in _records(item.get("source_register")):
            key = (
                str(source.get("provider") or ""),
                str(source.get("source_url") or ""),
                str(source.get("source_status") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            source_rows.append(source)
    readiness = desk.get("readiness") if isinstance(desk.get("readiness"), dict) else {}
    unavailable = [
        {
            "capability": capability,
            "source_status": "unavailable",
            "data_gap": f"{capability.replace('_', ' ').title()} is unavailable or unverified.",
        }
        for capability in ("hosted_persistence", "external_delivery")
        if readiness.get(capability) == "unavailable"
    ]
    return _envelope(
        "attention_desk",
        desk,
        summary=desk.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        caveats=[
            "Attention composition reads stored observations and makes zero market-provider calls.",
            "Retrieval-clock-only changes are not promoted as material attention rows.",
            "The deterministic digest is source-linked research information, not a recommendation, target, urgency claim, or order action.",
        ],
    )


def build_api_attention_action_payload(
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    payload_type: str,
    status: str = "ready",
) -> dict[str, Any]:
    safe = to_json_safe(data)
    row_count = len(safe) if isinstance(safe, list) else (1 if safe else 0)
    return _envelope(
        payload_type,
        safe,
        summary={"status": status, "row_count": row_count, "provider_call_count": 0},
        caveats=[
            "Identity is derived from the server session; client tenant and user fields are rejected.",
            "Attention state changes do not alter provider observation or retrieval clocks and make zero market-provider calls.",
        ],
    )


def build_api_observation_run_payload(
    data: dict[str, Any] | list[dict[str, Any]],
    *,
    payload_type: str = "observation_run",
    status: str | None = None,
) -> dict[str, Any]:
    safe = to_json_safe(data)
    if isinstance(safe, dict):
        run_status = status or str(safe.get("status") or "ready")
        provider_calls = int(safe.get("provider_call_count") or 0)
        row_count = len(_records(safe.get("runs"))) if "runs" in safe else (1 if safe else 0)
    else:
        run_status = status or "ready"
        provider_calls = 0
        row_count = len(safe)
    return _envelope(
        payload_type,
        safe,
        summary={
            "status": run_status,
            "row_count": row_count,
            "provider_call_count": provider_calls,
        },
        caveats=[
            "The run is explicit, bounded, quota-aware, and scoped to a server-derived tenant.",
            "Configured, contacted, cached, stale, partial, and unavailable provider states remain distinct.",
            "Observation runs provide research evidence only and do not place orders or send external alerts.",
        ],
    )


def build_api_watchlist_alert_manager_payload(
    contract: dict[str, Any] | None = None,
    *,
    payload_type: str = "watchlist_alert_manager",
    status: str | None = None,
) -> dict[str, Any]:
    data = to_json_safe(contract or build_watchlist_alert_manager_fixture_contract())
    summary = dict(data.get("summary") or {}) if isinstance(data, dict) else {}
    if status:
        summary["status"] = status
    summary.setdefault("provider_call_count", 0)
    triggers = _records(data.get("triggers") if isinstance(data, dict) else [])
    source_rows = [
        {
            "provider": row.get("provider") or "stored-observation",
            "source_url": row.get("source_url") or "",
            "source_status": row.get("source_status") or "unavailable",
            "observed_at": (row.get("clocks") or {}).get("observed_at") if isinstance(row.get("clocks"), dict) else None,
            "retrieved_at": (row.get("clocks") or {}).get("retrieved_at") if isinstance(row.get("clocks"), dict) else None,
            "trigger_id": row.get("trigger_id"),
            "caveat": row.get("caveat") or "",
            "data_gap": row.get("data_gap") or "",
        }
        for row in triggers
    ]
    hosted = data.get("hosted_readiness") if isinstance(data, dict) and isinstance(data.get("hosted_readiness"), dict) else {}
    channels = data.get("delivery_channels") if isinstance(data, dict) and isinstance(data.get("delivery_channels"), dict) else {}
    unavailable = []
    if hosted.get("status") != "available":
        unavailable.append({"capability": "hosted_alert_scheduling", "source_status": "unavailable", "caveat": hosted.get("caveat") or "Hosted alert scheduling is unverified."})
    unavailable.extend(
        {"capability": f"alert_delivery_{name}", "source_status": "unavailable", "caveat": "Phase 6O supports in-app delivery only."}
        for name, channel_status in channels.items()
        if name != "in_app" and channel_status == "unavailable"
    )
    return _envelope(
        payload_type,
        data,
        summary=summary,
        source_status=source_rows,
        unavailable=unavailable,
        caveats=[
            "Alert Manager reads, filters, evaluates, and reviews validated stored observations with zero market-provider calls.",
            "Stale or unavailable evidence never creates a live market-condition trigger; source-degradation rules retain their degraded source label.",
            "The manager is research monitoring only and provides no recommendation, external delivery, broker action, or autonomous execution.",
        ],
    )


def build_api_hosted_scheduler_operations_payload(
    contract: dict[str, Any] | None = None,
    *,
    payload_type: str = "hosted_scheduler_operations",
    status: str | None = None,
) -> dict[str, Any]:
    data = to_json_safe(contract or build_fixture_hosted_scheduler_contract("hosted-unverified"))
    summary = dict(data.get("summary") or {}) if isinstance(data, dict) else {}
    if status:
        summary["status"] = status
    summary.setdefault("provider_call_count", 0)
    runs = _records(data.get("runs") if isinstance(data, dict) else [])
    source_rows = [
        {
            "provider": (row.get("source") or {}).get("provider") or "hosted-scheduler",
            "source_url": (row.get("source") or {}).get("source_url") or "",
            "source_status": (row.get("source") or {}).get("source_status") or "unavailable",
            "observed_at": (row.get("clocks") or {}).get("observed_at"),
            "retrieved_at": (row.get("clocks") or {}).get("retrieved_at"),
            "scheduler_run_id": row.get("scheduler_run_id"),
            "caveat": (row.get("result") or {}).get("caveat") or "",
            "data_gap": (row.get("result") or {}).get("data_gap") or "",
        }
        for row in runs
        if isinstance(row.get("source"), dict) and isinstance(row.get("clocks"), dict)
    ]
    readiness = data.get("readiness") if isinstance(data, dict) and isinstance(data.get("readiness"), dict) else {}
    unavailable = []
    if readiness.get("hosted_scheduler_verified") is not True:
        unavailable.append(
            {
                "capability": "verified_hosted_recurring_observation",
                "source_status": "unavailable",
                "caveat": "A configured or fixture schedule is not hosted proof. A real deployed invocation and owner handoff must pass first.",
            }
        )
    return _envelope(
        payload_type,
        data,
        summary=summary,
        source_status=source_rows,
        unavailable=unavailable,
        caveats=[
            "Page reads and schedule controls make zero market-provider calls; only a successfully leased due run may spend its bounded quota.",
            "The runner is at-least-once with idempotent effects, not an exactly-once delivery claim.",
            "Hosted scheduling remains disabled and unverified until deployment evidence, A/B isolation, failure, recovery, and cleanup gates pass.",
            "This surface provides research monitoring only, with no external delivery, recommendation, broker action, or autonomous trade execution.",
        ],
    )


def build_api_market_intelligence_payload(*, include_runtime: bool = False) -> dict[str, Any]:
    workspace = build_market_intelligence_contract(include_runtime=include_runtime)
    source_rows = _workspace_source_rows(workspace)
    return _envelope(
        "market_intelligence",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=_workspace_unavailable_rows(source_rows),
        errors=_workspace_error_rows(source_rows),
        caveats=[
            "Market Intelligence rows are source/status-labeled and may be fixture, proxy, cached, stale, or unavailable.",
            "No broker execution, order routing, or directional market advice is provided.",
        ],
    )


def build_api_equity_intelligence_payload(symbol: str = "AAPL", *, include_runtime: bool = False) -> dict[str, Any]:
    workspace = build_equity_intelligence_contract(symbol=symbol, include_runtime=include_runtime)
    source_rows = _workspace_source_rows(workspace)
    return _envelope(
        "equity_intelligence",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=_workspace_unavailable_rows(source_rows),
        errors=_workspace_error_rows(source_rows),
        caveats=[
            "Equity Intelligence is read-only research context with explicit provider gaps.",
            "Options/gamma and financial-statement panels remain provider-gated when data is unavailable.",
            "No broker execution, order routing, or directional market advice is provided.",
        ],
    )


def build_api_financial_fundamentals_payload(symbol: str = "AAPL", *, include_runtime: bool = False) -> dict[str, Any]:
    workspace = build_financial_fundamentals_contract(symbol=symbol, include_runtime=include_runtime)
    source_rows = _records(workspace.get("source_register"))
    unavailable = _records(workspace.get("unavailable_sources"))
    return _envelope(
        "financial_fundamentals",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows(source_rows),
        caveats=[
            "Financial/Fundamentals is a dedicated read-only research workstation with visible source and data-gap rows.",
            "Missing statements, estimates, filings, and premium fundamentals remain provider-required or unavailable rather than inferred.",
            "No account action, execution pathway, or directional market advice is provided.",
        ],
    )


def build_api_options_quant_payload(symbol: str = "AAPL", *, expiry: str | None = None, include_runtime: bool = False) -> dict[str, Any]:
    workspace = build_options_quant_contract(symbol=symbol, expiry=expiry, include_runtime=include_runtime)
    source_rows = _records(workspace.get("source_register"))
    unavailable = _records(workspace.get("unavailable_sources"))
    return _envelope(
        "options_quant",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows(source_rows),
        caveats=[
            "Options/Quant is a research-only workstation with source-labeled option-chain, volatility, Greeks, quality, and scenario coverage.",
            "Gamma exposure is assumption-dependent research output; observed dealer positioning and institutional flow are not claimed.",
            "No account action, execution pathway, or directional market advice is provided.",
        ],
    )


def build_api_portfolio_risk_payload(
    *,
    portfolio_id: str = "demo-core",
    period: str = "1y",
    benchmark: str = "SPY",
    include_runtime: bool = False,
    holdings: Any = None,
) -> dict[str, Any]:
    workspace = build_portfolio_risk_workstation_contract(
        portfolio_id=portfolio_id,
        period=period,
        benchmark=benchmark,
        include_runtime=include_runtime,
        holdings=holdings,
    )
    source_rows = _records(workspace.get("source_register"))
    unavailable = _workspace_unavailable_rows(source_rows)
    if not workspace.get("holdings"):
        unavailable.append(
            {
                "provider": "portfolio input",
                "source_status": "unavailable",
                "availability": "unavailable",
                "error": "No valid holdings are available.",
                "recommended_action": "Use the deterministic demo or supply valid local-private holdings.",
            }
        )
    return _envelope(
        "portfolio_risk",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows(source_rows),
        caveats=[
            "Portfolio inputs are fictional demo rows or local-private research inputs; only symbols are sent to public market-data providers.",
            "Missing prices and returns remain unavailable and are never normalized to zero.",
            "Performance, risk, factor, attribution, and stress outputs are historical or assumption-bound research, not recommendations.",
            "No broker connection, rebalance instruction, position sizing, trade approval, autonomous action, or execution pathway is provided.",
        ],
    )


def build_api_research_memory_payload(
    *,
    mode: str = "demo",
    collection_id: str = "demo-research",
    surface: str = "inbox",
    memory_type: str = "",
    tag: str = "",
    db_path: Any = None,
) -> dict[str, Any]:
    workspace = build_research_memory_contract(
        mode=mode,
        collection_id=collection_id,
        surface=surface,
        memory_type=memory_type,
        tag=tag,
        db_path=db_path,
    )
    source_rows = _records(workspace.get("source_history"))
    unavailable = []
    readiness = workspace.get("readiness") or {}
    if readiness.get("store_status") != "ready":
        unavailable.append(
            {
                "provider": "local research store",
                "source_status": "unavailable",
                "availability": "unavailable",
                "error": readiness.get("error") or "Local store is unavailable.",
                "recommended_action": "Inspect the local SQLite store or use deterministic demo mode.",
            }
        )
    return _envelope(
        "research_memory",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows(unavailable),
        caveats=[
            "Demo rows are deterministic and fictional; local rows are private to the local workstation.",
            "Private note text, holdings, attachments, account data, and local paths are excluded from static fixtures and sanitized exports.",
            "Research Memory is non-advisory and does not enable broker actions, cloud sync, external AI, or autonomous monitoring.",
        ],
    )


def build_api_screener_drilldown_payload(*, include_runtime: bool = False) -> dict[str, Any]:
    workspace = build_screener_drilldown_contract(include_runtime=include_runtime)
    source_rows = _records(workspace.get("source_register"))
    unavailable = _records(workspace.get("unavailable_sources"))
    return _envelope(
        "screener_drilldown",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows(source_rows),
        caveats=[
            "Screener drilldown maps heatmap tiles to research workstations while preserving fixture/provider-required state.",
            "Live screening requires provider-backed universe, market cap, returns, and fundamentals before any live claim.",
            "No recommendation, account action, execution pathway, or directional market advice is provided.",
        ],
    )


def build_api_market_map_screener_payload(*, include_runtime: bool = False, period: str = "3mo") -> dict[str, Any]:
    workspace = build_market_map_screener_contract(include_runtime=include_runtime, period=period)
    source_rows = _records(workspace.get("source_register"))
    unavailable = _records(workspace.get("unavailable_sources"))
    return _envelope(
        "market_map_screener",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows(source_rows),
        caveats=[
            "Market Map ranks transparent historical metrics; it does not recommend securities or predict returns.",
            "Runtime quote history and static taxonomy have separate provenance and freshness states.",
            "Missing values are excluded from rank calculations rather than treated as zero.",
        ],
    )


def build_api_crypto_intelligence_payload(symbol: str = "BTCUSDT", *, include_runtime: bool = False) -> dict[str, Any]:
    workspace = build_crypto_intelligence_contract(symbol=symbol, include_runtime=include_runtime)
    source_rows = _workspace_source_rows(workspace)
    return _envelope(
        "crypto_intelligence",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=_workspace_unavailable_rows(source_rows),
        errors=_workspace_error_rows(source_rows),
        caveats=[
            "Crypto Intelligence uses public/free-first or fixture rows with visible source status.",
            "No exchange account action, broker execution, order routing, or directional market advice is provided.",
        ],
    )


def build_api_symbol_directory_payload(
    *,
    query: str = "",
    asset_class: str | None = None,
    limit: int = 20,
    include_materialized: bool = True,
) -> dict[str, Any]:
    workspace = build_symbol_directory_contract(
        query=query,
        asset_class=asset_class,
        limit=limit,
        include_materialized=include_materialized,
    )
    source_rows = _records(workspace.get("source_register"))
    return _envelope(
        "symbol_directory",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=[],
        errors=_workspace_error_rows(source_rows),
        caveats=[
            "The runtime symbol directory additively combines reviewed static rows with the current materialized Nasdaq/SEC-reconciled identities; it is not a complete security master.",
            "Static taxonomy and current provider/listing availability are separate states.",
            "No external FinanceDatabase rows, paid-provider payloads, account actions, or recommendations are included.",
        ],
    )


def build_api_symbol_workstation_payload(
    *,
    symbol: str = "AAPL",
    asset_class: str | None = None,
    interval: str = "1d",
    range_name: str = "3mo",
    runtime_mode: str = "fixture",
    chart_type: str = "candlestick",
    panels: str | list[str] | None = None,
    compare: str | None = None,
    fixture_catalog: bool = False,
) -> dict[str, Any]:
    workspace = (
        build_symbol_intelligence_fixture_catalog()
        if fixture_catalog
        else build_symbol_intelligence_contract(
            symbol,
            asset_class=asset_class,
            interval=interval,
            range_name=range_name,
            runtime_mode=runtime_mode,
            chart_type=chart_type,
            panels=panels,
            compare=compare,
        )
    )
    source_rows = _records(workspace.get("source_register"))
    unavailable = _records(workspace.get("unavailable_sources"))
    return _envelope(
        "symbol_workstation",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows([*source_rows, *unavailable]),
        caveats=[
            "Every workstation row is scoped to one resolved symbol; unknown symbols never receive another symbol's fixture.",
            "Fixture rows are deterministic synthetic values. Runtime rows can be live/fresh, cached, stale, unavailable, or provider-error.",
            "History cache keys include asset class, symbol, interval, and range; missing values remain null.",
            "Retrieval time and last market observation time are separate; a fresh retrieval does not imply a real-time quote.",
            "Technical outputs are historical calculations with explicit formulas and minimum observations.",
            "No broker execution, order routing, position sizing, or directional recommendation is provided.",
        ],
    )


def build_api_symbol_delivery_payload(
    *,
    symbol: str,
    delivery: str,
    asset_class: str | None = None,
    interval: str = "1d",
    range_name: str = "3mo",
    runtime_mode: str = "cache",
    chart_type: str = "candlestick",
    compare: str | None = None,
) -> dict[str, Any]:
    workspace = build_symbol_delivery_contract(
        symbol,
        asset_class=asset_class,
        interval=interval,
        range_name=range_name,
        runtime_mode=runtime_mode,
        chart_type=chart_type,
        delivery=delivery,
        compare=compare,
    )
    source_rows = _records(workspace.get("source_register"))
    unavailable = _records(workspace.get("unavailable_sources"))
    return _envelope(
        "symbol_workstation",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows([*source_rows, *unavailable]),
        caveats=[
            "Summary delivery never refreshes a provider; chart-core, technicals, and detail panels are exact-symbol on-demand contracts.",
            "Panel cache keys remain scoped by symbol, asset class, interval, range, panel version, and optional comparison.",
            "No panel may substitute another symbol, fabricate live rows, place orders, or provide directional recommendations.",
        ],
    )


def build_api_analyst_workspace_payload(
    *,
    symbol: str,
    asset_class: str | None = None,
    interval: str = "1d",
    range_name: str = "3mo",
    runtime_mode: str = "cache",
    compare: str | None = None,
    layout: dict[str, Any] | None = None,
    return_state: dict[str, Any] | None = None,
    change_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workspace = build_analyst_workspace_contract(
        symbol,
        asset_class=asset_class,
        interval=interval,
        range_name=range_name,
        runtime_mode=runtime_mode,
        compare=compare,
        layout=layout,
        return_state=return_state,
        change_context=change_context,
    )
    source_rows = _records(workspace.get("source_register"))
    unavailable = [
        row
        for row in _records(workspace.get("panels"))
        if row.get("compatibility") == "not_applicable"
        or row.get("source_status") in {"unavailable", "provider-error"}
    ]
    return _envelope(
        "analyst_workspace",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows(unavailable),
        caveats=[
            "The initial workspace contains compact identity and panel references, not duplicated chart, financial, or news rows.",
            "Desktop and mobile clients progressively request exact-symbol panels and must retain only same-identity last-known-good evidence.",
            "Layout persistence is local-only; no hosted synchronization, broker execution, or autonomous AI action is provided.",
        ],
    )


def build_api_research_operations_payload(
    request: dict[str, Any],
    *,
    store: ResearchOperationsStore | None = None,
) -> dict[str, Any]:
    contract = build_research_operations_contract(request, store=store)
    providers = _records(contract.get("provider_health"))
    unavailable = [
        row
        for row in providers
        if row.get("availability") == "unavailable"
        or row.get("status")
        in {
            "configured",
            "missing-key",
            "unavailable",
            "forbidden/subscription-blocked",
        }
    ]
    summary = {
        "workspace": "research-operations",
        "symbol": contract.get("identity", {}).get("symbol"),
        "panel_count": len(_records(contract.get("panels"))),
        "observed_provider_count": contract.get("readiness", {}).get(
            "observed_provider_count",
            0,
        ),
        "queue_status": contract.get("queue", {}).get("status"),
        "last_attempt_status": contract.get("last_attempt", {}).get("status"),
        "last_success_available": bool(contract.get("last_success")),
        "planned_calls": contract.get("budget", {}).get("planned_calls"),
        "hard_ceiling": contract.get("budget", {}).get("hard_ceiling"),
    }
    return _envelope(
        "research_operations",
        contract,
        summary=summary,
        source_status=providers,
        unavailable=unavailable,
        errors=[
            row
            for row in providers
            if row.get("status")
            in {"provider-error", "rate-limited", "forbidden/subscription-blocked"}
        ],
        caveats=[
            "Configured provider credentials are not promoted to successful until an exact panel observation records contact and usable evidence.",
            "Retrieval and market/event observation clocks remain separate; a fresh retrieval can still contain an older observation.",
            "The refresh worker is process-local and bounded. No installed service, hosted scheduler, notification delivery, broker action, or automatic retry is claimed.",
        ],
    )


def build_api_account_workspace_payload(
    context: dict[str, Any],
    *,
    provider_calls: int = 0,
    preference: dict[str, Any] | None = None,
    sync_state: str | None = None,
    persistence_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = build_account_workspace_contract(
        context,
        provider_calls=provider_calls,
        preference=preference,
        sync_state=sync_state,
        persistence_health=persistence_health,
    )
    persistence = contract.get("persistence") or {}
    unavailable = []
    if not persistence.get("hosted_verified"):
        unavailable.append(
            {
                "provider": persistence.get("provider") or "supabase",
                "source_status": persistence.get("source_status") or "unavailable",
                "data_gap": persistence.get("data_gap"),
                "caveat": persistence.get("caveat"),
            }
        )
    return _envelope(
        "account_workspace",
        contract,
        summary=contract.get("summary") or {},
        source_status=[persistence],
        unavailable=unavailable,
        caveats=[
            "Local-test identity remains QA-only; hosted status requires a verified user session and observed RLS-bound repository operations.",
            "Tenant identity is derived from the server-side session and is never accepted from preference JSON.",
            "Checkout, payment collection, broker action, and autonomous action remain disabled.",
        ],
    )


def build_api_account_preference_payload(
    preference: dict[str, Any] | None,
    *,
    status: str,
    persistence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    persistence_row = persistence if isinstance(persistence, dict) else None
    persistence_status = str((persistence_row or {}).get("status") or "")
    hosted_verified = bool(
        (persistence_row or {}).get("remote_contacted")
        and persistence_status in {"applied", "deduped"}
    )
    data = {
        **(preference or {}),
        "status": status,
        "hosted_verified": hosted_verified,
        **({"persistence": persistence_row} if persistence_row is not None else {}),
        "not_financial_advice": True,
    }
    return _envelope(
        "account_preference",
        data,
        summary={
            "status": status,
            "available": preference is not None,
            "version": (preference or {}).get("version"),
        },
        caveats=[
            (
                "This tenant-scoped preference was confirmed by the authenticated hosted repository."
                if hosted_verified
                else "This preference has no confirmed hosted write evidence in this response."
            )
        ],
    )


def build_api_tenant_research_desk_payload(
    contract: dict[str, Any],
    *,
    payload_type: str = "tenant_research_desk",
    status: str = "ready",
) -> dict[str, Any]:
    data = to_json_safe(contract)
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    unavailable = []
    readiness = data.get("readiness") if isinstance(data.get("readiness"), dict) else {}
    for capability in ("hosted_persistence", "external_delivery"):
        if readiness.get(capability) == "unavailable":
            unavailable.append(
                {
                    "capability": capability,
                    "source_status": "unavailable",
                    "data_gap": f"{capability.replace('_', ' ').title()} is not implemented or verified.",
                }
            )
    return _envelope(
        payload_type,
        data,
        summary={"status": status, **summary},
        unavailable=unavailable,
        caveats=[
            "Tenant ownership is derived from the authenticated server session; client identity fields are rejected.",
            "Import preview is read-only and bounded; it makes no provider calls and excludes local private notes.",
            "Saved-change delivery is in-app only. Hosted delivery, broker execution, and autonomous action remain unavailable.",
        ],
    )


def build_api_research_refresh_job_payload(
    job: dict[str, Any],
) -> dict[str, Any]:
    public_job = to_json_safe(job)
    status = str(public_job.get("status") or "unavailable")
    return _envelope(
        "research_refresh_job",
        public_job,
        summary={
            "job_id": public_job.get("job_id"),
            "symbol": public_job.get("symbol"),
            "status": status,
            "planned_calls": public_job.get("planned_calls", 0),
            "actual_calls": public_job.get("actual_calls", 0),
            "retained_lkg": bool(public_job.get("retained_lkg")),
        },
        source_status=[public_job],
        unavailable=[public_job]
        if status in {"failed", "rate-limited", "overlap"}
        else [],
        errors=[public_job] if status == "failed" else [],
        caveats=[
            "Job history contains bounded public operational metadata only.",
            "A terminal failure never replaces a prior same-symbol successful panel body.",
            "No blind retry, broad watchlist fan-out, hosted worker, or execution action is provided.",
        ],
    )


def build_api_watchlist_desk_payload(
    *,
    mode: str = "fixture",
    list_id: str = "primary",
    selected_symbol: str | None = None,
) -> dict[str, Any]:
    normalized_mode = str(mode or "fixture").lower()
    if normalized_mode not in {"fixture", "local"}:
        raise ValueError("Watchlist Desk mode must be fixture or local.")
    workspace = (
        build_watchlist_desk_fixture_contract()
        if normalized_mode == "fixture"
        else build_watchlist_desk_contract(list_id=list_id, selected_symbol=selected_symbol)
    )
    items = _records(workspace.get("items"))
    source_rows = []
    for row in items:
        source_rows.append(
            {
            "provider": row.get("market_provider") or "watchlist-identity-store",
            "source": row.get("symbol"),
            "source_url": row.get("market_source_url"),
            "fetched_at": row.get("market_fetched_at") or row.get("refresh_fetched_at"),
            "freshness": row.get("freshness"),
            "source_status": row.get("source_status"),
            "row_count": 1,
            "caveat": "Watchlist quote context can be delayed; exact workstation panels load independently.",
            "data_gap": row.get("refresh_data_gap"),
            "not_financial_advice": True,
            }
        )
        source_rows.extend(_records(row.get("source_register")))
    unavailable = [
        row
        for row in items
        if row.get("identity_status") != "exact" or row.get("source_status") == "unavailable"
    ]
    return _envelope(
        "watchlist_desk",
        workspace,
        summary=workspace.get("summary") or {},
        source_status=source_rows,
        unavailable=unavailable,
        errors=_workspace_error_rows([*source_rows, *unavailable]),
        caveats=[
            "Watchlist names, symbols, order, and private reasons are stored locally; private reasons are excluded from this payload.",
            "Materialization is manual, bounded, and overlap-protected. No installed background service is claimed.",
            "Quotes may be delayed and all outputs are read-only research context.",
        ],
    )


def build_api_watchlist_change_payload(
    *,
    mode: str = "local",
    list_id: str = "primary",
) -> dict[str, Any]:
    normalized_mode = str(mode or "local").lower()
    if normalized_mode not in {"fixture", "local"}:
        raise ValueError("Watchlist change mode must be fixture or local.")
    if normalized_mode == "fixture":
        workspace = build_watchlist_desk_fixture_contract()
        data = {
            "list_id": "fixture-daily",
            "list_name": "Daily Radar",
            "change_inbox": workspace.get("change_inbox") or {},
            "refresh_operations": workspace.get("refresh_operations") or {},
            "alert_readiness": workspace.get("alert_readiness") or {},
            "privacy_scope": "fictional-demo",
            "provider_call_count": 0,
            "caveat": "Fictional saved-snapshot comparison for deterministic product QA.",
            "not_financial_advice": True,
        }
    else:
        data = build_watchlist_change_contract(list_id)
    diff = data.get("change_inbox") if isinstance(data.get("change_inbox"), dict) else {}
    changes = _records(diff.get("changes"))
    source_rows = []
    for change in changes:
        evidence = change.get("evidence") if isinstance(change.get("evidence"), dict) else {}
        for side in ("before", "after"):
            row = evidence.get(side) if isinstance(evidence.get(side), dict) else {}
            if row:
                source_rows.append({**row, "symbol": change.get("symbol"), "change_id": change.get("change_id"), "side": side})
    return _envelope(
        "watchlist_desk",
        data,
        summary={
            "list_id": data.get("list_id"),
            "comparison_status": diff.get("comparison_status"),
            "change_count": len(changes),
            "provider_call_count": 0,
            "alert_status": (data.get("alert_readiness") or {}).get("status")
            if isinstance(data.get("alert_readiness"), dict)
            else "unavailable",
            "non_advisory": True,
        },
        source_status=source_rows,
        unavailable=[] if diff.get("comparison_status") == "ready" else [{"status": diff.get("comparison_status"), "data_gap": diff.get("data_gap")}],
        errors=[],
        caveats=[
            "This endpoint compares saved same-list observations and makes zero provider calls.",
            "Change materiality is a documented calculation threshold, not investment significance or advice.",
            "Notification delivery is preview-only; hosted email, SMS, push, webhook, broker, and autonomous actions are unavailable.",
        ],
    )


def build_api_feed_registry_payload(feeds: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = _records(feeds if feeds is not None else build_feed_registry())
    summary = {
        "feed_count": len(rows),
        "default_enabled_count": sum(1 for row in rows if row.get("default_enabled")),
        "requires_key_count": sum(1 for row in rows if row.get("requires_key")),
        "categories": sorted({str(row.get("category")) for row in rows if row.get("category")}),
        "providers": sorted({str(row.get("provider")) for row in rows if row.get("provider")}),
        "source_types": sorted({str(row.get("source_type")) for row in rows if row.get("source_type")}),
    }
    unavailable = [row for row in rows if row.get("requires_key") or row.get("default_enabled") is False]
    return _envelope(
        "feed_registry",
        rows,
        summary=summary,
        unavailable=unavailable,
        caveats=[
            "Feed registry is network-free metadata; live availability is reported by provider health payloads.",
            "Optional paid/keyed feeds remain disabled until explicitly configured and probed.",
        ],
    )


def build_api_provider_health_payload(
    results: Iterable[Any] | None = None,
    *,
    ledger: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _records(ledger if ledger is not None else build_provider_health_ledger(list(results if results is not None else get_recent_results())))
    summary = summarize_provider_health_ledger(rows)
    unavailable = [
        row
        for row in rows
        if row.get("availability") == "unavailable"
        or row.get("status") in {"missing-key", "unavailable", "forbidden/subscription-blocked"}
    ]
    errors = [row for row in rows if row.get("error")]
    return _envelope(
        "provider_health",
        rows,
        summary=summary,
        source_status=rows,
        unavailable=unavailable,
        errors=errors,
        caveats=[
            "Provider health is evidence-led; partial failures stay visible beside successful providers.",
            "Missing optional paid keys are represented as unavailable or missing-key states, not failures of free mode.",
        ],
    )


def build_api_layer_runtime_payload(
    runtime_feeds: dict[str, Any] | None = None,
    statuses: Iterable[Any] | None = None,
    layers: list[dict[str, Any]] | None = None,
    *,
    layer_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = to_json_safe(layer_payload if layer_payload is not None else build_layer_runtime_payload(runtime_feeds, list(statuses or []), layers))
    layer_rows = _records(payload.get("layers") if isinstance(payload, dict) else [])
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    unavailable = [row for row in layer_rows if row.get("availability") == "unavailable"]
    status_rows = _status_records(statuses)
    if runtime_feeds:
        status_rows.extend(_records(runtime_feeds.get("source_status")))
        status_rows.extend(_records(runtime_feeds.get("source_statuses")))
    return _envelope(
        "layer_runtime",
        {"layers": layer_rows},
        summary=summary,
        source_status=status_rows,
        unavailable=unavailable,
        caveats=[
            payload.get("caveat", "") if isinstance(payload, dict) else "",
            "Layer rows are JSON-safe and omit Streamlit/Plotly rendering objects.",
        ],
    )


def build_api_news_dashboard_payload(
    items: Any = None,
    statuses: Iterable[Any] | None = None,
    *,
    dashboard: dict[str, Any] | None = None,
    max_rows: int = 100,
) -> dict[str, Any]:
    source_dashboard = (
        dashboard
        if dashboard is not None
        else build_worldmonitor_style_news_dashboard([] if items is None else items, statuses)
    )
    data = {
        "normalized_news": _records(source_dashboard.get("normalized_news"), limit=max_rows),
        "high_severity_feed": _records(source_dashboard.get("high_severity_feed"), limit=max_rows),
        "timeline": _records(source_dashboard.get("timeline"), limit=max_rows),
        "impact_matrix": _records(source_dashboard.get("impact_matrix"), limit=max_rows),
        "regional_cards": _records(source_dashboard.get("regional_cards"), limit=max_rows),
        "source_freshness": _records(source_dashboard.get("source_freshness"), limit=max_rows),
        "event_rows": _records(source_dashboard.get("event_rows"), limit=max_rows),
        "risk_catalysts": to_json_safe(source_dashboard.get("risk_catalysts") or []),
        "notes": to_json_safe(source_dashboard.get("notes") or []),
    }
    summary = to_json_safe(source_dashboard.get("source_status_summary") or {})
    unavailable = []
    if summary.get("status") == "unavailable":
        unavailable.append({"area": "news_dashboard", "status": "unavailable", "caveat": summary.get("caveat")})
    errors = [row for row in data["source_freshness"] if row.get("error")]
    return _envelope(
        "news_dashboard",
        data,
        summary=summary,
        source_status=list(statuses or []) + data["source_freshness"],
        unavailable=unavailable,
        errors=errors,
        caveats=[
            "News rows are deterministic public-feed classifications and may contain approximate coordinates.",
            "WorldMonitor remains a workflow reference only; no external runtime code is imported.",
        ],
    )


def _map_summary(map_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = map_payload or {}
    frame_rows = _records(payload.get("frame"))
    chokepoint_rows = _records(payload.get("chokepoint_frame"))
    return {
        "selected_layers": to_json_safe(payload.get("selected_layers") or []),
        "event_row_count": len(frame_rows),
        "chokepoint_row_count": len(chokepoint_rows),
        "status": to_json_safe(payload.get("status")),
        "chokepoint_status": to_json_safe(payload.get("chokepoint_status")),
        "caveat": payload.get("caveat"),
    }


def build_api_war_room_payload(
    state: dict[str, Any] | None = None,
    *,
    include_default_runtime: bool = False,
    max_events: int = 100,
) -> dict[str, Any]:
    if state is None:
        from .war_room import build_data_gap_panel, build_war_room_state

        state = build_war_room_state(include_default_runtime=include_default_runtime)
        data_gaps = _records(build_data_gap_panel(state))
    else:
        from .war_room import build_data_gap_panel

        data_gaps = _records(build_data_gap_panel(state))
    layer_runtime = to_json_safe(state.get("layer_runtime_status") or {})
    provider_health = to_json_safe(state.get("provider_health_ledger") or {})
    layer_rows = _records(layer_runtime.get("layers") if isinstance(layer_runtime, dict) else [])
    provider_rows = _records(provider_health.get("ledger") if isinstance(provider_health, dict) else [])
    events = _records(state.get("events"), limit=max_events)
    data = {
        "header_metrics": to_json_safe(state.get("header_metrics") or {}),
        "events": events,
        "event_timeline": _records(state.get("event_timeline")),
        "map_summary": _map_summary(state.get("map_payload") or {}),
        "layer_runtime_status": layer_runtime,
        "provider_health_ledger": provider_health,
        "market_impact_summary": to_json_safe(state.get("market_impact_summary") or {}),
        "macro_energy_payload": to_json_safe(state.get("macro_energy_payload") or {}),
        "runtime_feeds": to_json_safe(state.get("runtime_feeds") or {}),
        "ai_context": to_json_safe(state.get("ai_context") or {}),
        "data_gaps": data_gaps,
        "caveat": state.get("caveat"),
    }
    source_status = _records(state.get("source_status"))
    unavailable = [
        {"area": "layer_runtime", **row}
        for row in layer_rows
        if row.get("availability") == "unavailable"
    ]
    unavailable.extend(
        {"area": "provider_health", **row}
        for row in provider_rows
        if row.get("availability") == "unavailable"
        or row.get("status") in {"missing-key", "unavailable", "forbidden/subscription-blocked"}
    )
    errors = [row for row in source_status if row.get("error")]
    summary = {
        "event_count": len(events),
        "layer_count": (layer_runtime.get("summary") or {}).get("layer_count") if isinstance(layer_runtime, dict) else None,
        "provider_count": (provider_health.get("summary") or {}).get("provider_count") if isinstance(provider_health, dict) else None,
        "global_risk_state": data["header_metrics"].get("global_risk_state"),
        "data_freshness_summary": data["header_metrics"].get("data_freshness_summary"),
    }
    return _envelope(
        "war_room",
        data,
        summary=summary,
        source_status=source_status,
        unavailable=unavailable,
        errors=errors,
        caveats=[
            "War Room API payload omits Plotly figures, DataFrames, and Streamlit-only objects.",
            "Static chokepoints and heuristic scores remain proxy/context unless live providers are configured.",
        ],
    )


def build_api_ai_provider_payload(preferred: str = "auto") -> dict[str, Any]:
    providers = list_available_ai_providers()
    selected = select_ai_provider(preferred)
    grounding_enabled = str(os.getenv("GEMINI_ENABLE_GOOGLE_SEARCH") or "false").strip().lower() in {"1", "true", "yes", "on"}
    rows = [
        {
            "provider": item.provider,
            "model": item.model,
            "available": bool(item.available),
            "configured": bool(item.available),
            "env_var": item.env_var,
            "base_url_configured": bool(item.base_url),
            "is_local": bool(item.is_local),
            "is_free_mode": bool(item.is_free_mode),
            "source_status": "available" if item.available else "missing-key" if item.env_var else "unavailable",
            "warning": item.warning,
        }
        for item in providers
    ]
    unavailable = [row for row in rows if not row["available"]]
    summary = {
        "selected_provider": selected.provider,
        "selected_model": selected.model,
        "selected_available": bool(selected.available),
        "selected_free_mode": bool(selected.is_free_mode),
        "provider_count": len(rows),
        "available_count": sum(1 for row in rows if row["available"]),
        "free_first_order": ["gemini", "groq", "ollama", "openrouter", "anthropic", "rule_based"],
        "gemini_google_search_grounding_enabled": grounding_enabled,
        "openai_api_key_required": False,
    }
    return _envelope(
        "ai_provider_status",
        rows,
        summary=summary,
        source_status=rows,
        unavailable=unavailable,
        caveats=[
            "AI provider payload exposes configuration status only; secret values are never included.",
            "Gemini Google Search grounding remains opt-in because it may create billable tool usage.",
            "Rule-based fallback is always available and requires no paid API key.",
        ],
    )


def build_api_asset_universe_payload() -> dict[str, Any]:
    payload = build_asset_universe_contract()
    asset_rows = _records(payload.get("asset_classes"))
    command_rows = _records(payload.get("command_asset_matrix"))
    source_rows = [
        {
            "provider": "phase2e_native_contract",
            "source": "FinanceDatabase-main.zip schema evidence",
            "source_status": "reference-schema",
            "availability": "limited",
            "row_count": 0,
            "live_rows_claimed": False,
            "license_stance": "direct-use-allowed",
            "caveat": "MIT-licensed schema/taxonomy evidence; external CSV rows are not copied into fixtures.",
        }
    ]
    source_rows.extend(
        {
            "provider": "asset_universe",
            "source": row.get("evidence_ref"),
            "asset_class": row.get("asset_class"),
            "source_status": row.get("source_status"),
            "availability": "limited",
            "row_count": 0,
            "live_rows_claimed": False,
            "license_stance": row.get("license_stance"),
            "caveat": row.get("caveat"),
        }
        for row in asset_rows
    )
    unavailable = [
        {
            "asset_class": row.get("asset_class"),
            "status": row.get("local_status"),
            "availability": "limited",
            "recommended_action": "Configure or build a provider-backed symbol universe before claiming live coverage.",
            "caveat": row.get("caveat"),
        }
        for row in asset_rows
        if not row.get("live_rows_claimed")
    ]
    summary = {
        "asset_class_count": len(asset_rows),
        "command_count": len(command_rows),
        "schema_ready": bool((payload.get("readiness") or {}).get("schema_ready")),
        "live_rows_claimed": False,
        "external_rows_copied": False,
        "reference_project": "FinanceDatabase",
        "license_stance": "direct-use-allowed",
    }
    return _envelope(
        "asset_universe",
        payload,
        summary=summary,
        source_status=source_rows,
        unavailable=unavailable,
        caveats=[
            "Phase 2E adopts FinanceDatabase asset-universe schema behavior under MIT evidence; external rows are not vendored.",
            "This payload is a reference-schema contract, not a live security master.",
            "Provider-backed symbol rows must carry their own source, freshness, and license metadata before being marked live.",
        ],
    )


def build_api_event_asset_graph_payload(
    *,
    events: Any = None,
    provider_rows: Any = None,
    asset_universe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph = build_event_asset_graph_contract(events=events, provider_rows=provider_rows, asset_universe=asset_universe)
    nodes = _records(graph.get("nodes"))
    edges = _records(graph.get("edges"))
    readiness = to_json_safe(graph.get("readiness") or {})
    unavailable = _records(readiness.get("unavailable_capabilities") if isinstance(readiness, dict) else [])
    source_status = [
        {
            "provider": node.get("provider") or "phase2f_event_asset_graph",
            "source": node.get("source_url") or node.get("id"),
            "source_status": node.get("source_status"),
            "confidence": node.get("confidence"),
            "fetched_at": node.get("fetched_at"),
            "node_id": node.get("id"),
            "node_type": node.get("type"),
            "caveat": node.get("caveat"),
        }
        for node in nodes
    ]
    source_status.extend(
        {
            "provider": edge.get("provider") or "phase2f_event_asset_graph",
            "source": edge.get("source_url") or edge.get("id"),
            "source_status": edge.get("source_status"),
            "confidence": edge.get("confidence"),
            "fetched_at": edge.get("fetched_at"),
            "edge_id": edge.get("id"),
            "relationship": edge.get("relationship"),
            "caveat": edge.get("caveat"),
        }
        for edge in edges
    )
    summary = {
        **to_json_safe(graph.get("summary") or {}),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "payload_mode": "deterministic-clean-room",
    }
    return _envelope(
        "event_asset_graph",
        graph,
        summary=summary,
        source_status=source_status,
        unavailable=unavailable,
        caveats=[
            "Event-to-asset links are source-backed where event/provider fields exist and inferred/proxy where rule-based market mapping is used.",
            "Graph persistence, live graph storage, user-specific graph state, hosted Supabase, and graph databases are unavailable in Phase 2F.",
            "External references inform behavior and product patterns only; blocked AGPL/NASA/missing-license source is not copied.",
        ],
    )


def build_api_command_workspace_payload(
    *,
    event_graph: dict[str, Any] | None = None,
    provider_rows: Any = None,
) -> dict[str, Any]:
    workspace = build_command_workspace_contract(event_graph=event_graph, provider_rows=provider_rows)
    commands = _records(workspace.get("commands"))
    contexts = _records(workspace.get("contexts"))
    command_results = _records(workspace.get("command_results"))
    provider_requirements = _records(workspace.get("provider_requirements"))
    readiness = to_json_safe(workspace.get("readiness") or {})
    readiness_unavailable = _records(readiness.get("unavailable_capabilities") if isinstance(readiness, dict) else [])
    unavailable = [
        *readiness_unavailable,
        *[
            {
                "command": row.get("command"),
                "status": row.get("result_status"),
                "provider": row.get("provider"),
                "recommended_action": (row.get("provider_requirement") or {}).get("recommended_action")
                if isinstance(row.get("provider_requirement"), dict)
                else "",
                "caveat": (row.get("preview") or {}).get("caveat") if isinstance(row.get("preview"), dict) else row.get("caveat"),
            }
            for row in command_results
            if not row.get("available")
        ],
    ]
    source_status = [
        {
            "provider": row.get("provider") or "phase3_command_workspace",
            "source": row.get("route") or row.get("command"),
            "source_status": row.get("source_status"),
            "fetched_at": row.get("fetched_at"),
            "command": row.get("command"),
            "implementation_status": row.get("implementation_status"),
            "caveat": row.get("caveat"),
        }
        for row in commands
    ]
    source_status.extend(
        {
            "provider": row.get("provider") or "phase3_command_workspace",
            "source": (row.get("provider_requirement") or {}).get("source") if isinstance(row.get("provider_requirement"), dict) else "",
            "source_status": row.get("source_status"),
            "fetched_at": row.get("fetched_at"),
            "command": row.get("command"),
            "result_status": row.get("result_status"),
            "caveat": (row.get("preview") or {}).get("caveat") if isinstance(row.get("preview"), dict) else "",
        }
        for row in command_results
    )
    source_status.extend(
        {
            "provider": row.get("provider") or "none",
            "source": row.get("provider_family") or row.get("command"),
            "source_status": row.get("status"),
            "fetched_at": row.get("fetched_at"),
            "command": row.get("command"),
            "caveat": row.get("caveat"),
        }
        for row in provider_requirements
    )
    summary = {
        **to_json_safe(workspace.get("summary") or {}),
        "payload_mode": "deterministic-clean-room",
        "command_count": len(commands),
        "context_count": len(contexts),
        "command_result_count": len(command_results),
    }
    return _envelope(
        "command_workspace",
        workspace,
        summary=summary,
        source_status=source_status,
        unavailable=unavailable,
        caveats=[
            "Command workspace actions are read-only workstation routes backed by source, provider status, caveat, and data-gap fields.",
            "Provider-required commands stay unavailable unless fresh or cached provider evidence is present.",
            "No market-action pathway, auth, billing, hosted persistence, graph database, or paid provider dependency is added in Phase 3.",
        ],
    )


def build_api_war_room_map_payload(
    *,
    state: dict[str, Any] | None = None,
    events: Any = None,
    layer_runtime: dict[str, Any] | None = None,
    provider_rows: Any = None,
    event_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = build_war_room_map_contract(
        state=state,
        events=events,
        layer_runtime=layer_runtime,
        provider_rows=provider_rows,
        event_graph=event_graph,
    )
    markers = _records(contract.get("markers"))
    layers = _records(contract.get("layers"))
    readiness = to_json_safe(contract.get("readiness") or {})
    readiness_unavailable = _records(readiness.get("unavailable_capabilities") if isinstance(readiness, dict) else [])
    provider_requirements = _records(contract.get("provider_requirements"))
    unavailable = [
        *readiness_unavailable,
        *[
            {
                "layer_id": row.get("layer_id"),
                "provider": row.get("provider"),
                "status": row.get("source_status"),
                "availability": row.get("availability"),
                "requires_key": row.get("requires_key"),
                "recommended_action": row.get("recommended_action"),
                "caveat": row.get("caveat"),
            }
            for row in layers
            if row.get("availability") == "unavailable"
        ],
        *[
            {
                "requirement_id": row.get("requirement_id"),
                "layer_id": row.get("layer_id"),
                "provider": row.get("provider"),
                "status": row.get("layer_status"),
                "provider_status": row.get("provider_status"),
                "recommended_action": row.get("recommended_action"),
                "caveat": row.get("caveat"),
            }
            for row in provider_requirements
            if not row.get("live_claim_allowed")
        ],
    ]
    source_status = [
        {
            "provider": marker.get("provider"),
            "source": marker.get("source_url") or marker.get("source"),
            "source_status": marker.get("source_status"),
            "fetched_at": marker.get("fetched_at"),
            "marker_id": marker.get("marker_id"),
            "coordinate_status": marker.get("coordinate_status"),
            "confidence": marker.get("confidence"),
            "caveat": marker.get("caveat"),
        }
        for marker in markers
    ]
    source_status.extend(
        {
            "provider": layer.get("provider"),
            "source": layer.get("source"),
            "source_status": layer.get("source_status"),
            "fetched_at": layer.get("latest_fetched_at"),
            "layer_id": layer.get("layer_id"),
            "availability": layer.get("availability"),
            "row_count": layer.get("row_count"),
            "caveat": layer.get("caveat"),
        }
        for layer in layers
    )
    summary = {
        **to_json_safe(contract.get("summary") or {}),
        "payload_mode": "map-first-clean-room",
        "marker_count": len(markers),
        "layer_count": len(layers),
    }
    return _envelope(
        "war_room_map",
        contract,
        summary=summary,
        source_status=source_status,
        unavailable=unavailable,
        caveats=[
            "War Room map markers require source/provider/freshness evidence or explicit proxy/static/fixture labeling.",
            "Approximate, fixture, and static coordinates are labeled on every marker.",
            "Live AIS, flight tracking, sanctions markers, broker execution, auth, billing, hosted persistence, graph databases, and paid provider dependencies are unavailable in Phase 4.",
            "External references inform behavior only; no AGPL/NASA/missing-license source or visual assets are copied.",
        ],
    )


def build_api_map_news_event_fusion_payload(
    *,
    war_room_map: dict[str, Any] | None = None,
    news_dashboard: dict[str, Any] | None = None,
    event_graph: dict[str, Any] | None = None,
    provider_health: dict[str, Any] | list[dict[str, Any]] | None = None,
    layer_runtime: dict[str, Any] | None = None,
    market_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = build_map_news_event_fusion_contract(
        war_room_map=war_room_map,
        news_dashboard=news_dashboard,
        event_graph=event_graph,
        provider_health=provider_health,
        layer_runtime=layer_runtime,
        market_intelligence=market_intelligence,
    )
    source_rows = _records(contract.get("source_register"))
    unavailable = _records(contract.get("unavailable_sources"))
    errors = [row for row in source_rows if row.get("error")]
    summary = {
        **to_json_safe(contract.get("summary") or {}),
        "payload_mode": "map-news-event-clean-room",
    }
    return _envelope(
        "map_news_event_fusion",
        contract,
        summary=summary,
        source_status=source_rows,
        unavailable=unavailable,
        errors=errors,
        caveats=[
            "Map-news-event fusion reuses existing source-labeled War Map, News, Event Graph, Provider, Layer, and Market Heatmap contracts.",
            "Fixture/proxy/static rows remain clearly labeled and never become live provider claims.",
            "External WorldMonitor/worldview/TradingView patterns inform behavior only; no blocked source or visual assets are copied.",
            "No broker execution path, account action, auth, billing, or directional market advice is provided.",
        ],
    )


def build_api_war_room_map_replay_payload(
    *,
    contract: dict[str, Any] | None = None,
    snapshot_id: str | None = None,
    compare_to: str | None = None,
    db_path: Any = None,
    demo: bool = False,
) -> dict[str, Any]:
    replay = contract or (
        build_demo_war_room_map_replay_contract()
        if demo
        else build_war_room_map_replay_contract(snapshot_id=snapshot_id, compare_to=compare_to, db_path=db_path)
    )
    active = replay.get("active_snapshot") if isinstance(replay.get("active_snapshot"), dict) else {}
    source_rows = _records(active.get("source_register"))
    unavailable = [
        row
        for row in [*_records(active.get("layers")), *_records(active.get("providers"))]
        if row.get("availability") == "unavailable"
        or str(row.get("source_status") or row.get("status") or "").lower()
        in {"unavailable", "missing-key", "provider-required", "forbidden/subscription-blocked"}
    ]
    snapshots = _records(replay.get("snapshots"))
    diff = replay.get("diff") if isinstance(replay.get("diff"), dict) else {}
    summary = {
        "payload_mode": "local-private-observed-replay" if not demo else "fictional-deterministic-replay",
        "historical_truth": replay.get("historical_truth"),
        "snapshot_count": len(snapshots),
        "active_snapshot_id": active.get("snapshot_id"),
        "comparison_snapshot_id": (replay.get("comparison_snapshot") or {}).get("snapshot_id")
        if isinstance(replay.get("comparison_snapshot"), dict)
        else None,
        "diff_summary": to_json_safe(diff.get("summary") or {}),
        "privacy_scope": replay.get("privacy_scope"),
    }
    return _envelope(
        "war_room_map_replay",
        replay,
        summary=summary,
        source_status=source_rows,
        unavailable=unavailable,
        caveats=[
            "Historical replay contains only project-captured observations or an explicitly fictional deterministic fixture.",
            "Removed rows do not prove real-world resolution, causality, or market impact.",
            "Snapshot content is local-private and excluded from deterministic fixture export and source releases.",
            "AIS, flight, sanctions, paid layers, broker execution, hosted sync, auth, and billing remain unavailable unless separately verified.",
        ],
    )


def build_api_daily_brief_payload(
    *,
    brief: dict[str, Any] | None = None,
    period: str = "morning",
    include_runtime: bool = False,
    db_path: Any = None,
    demo: bool = False,
) -> dict[str, Any]:
    contract = brief or (
        build_demo_daily_brief_contract()
        if demo
        else build_current_daily_brief_contract(period=period, include_runtime=include_runtime, db_path=db_path)
    )
    sources = _records(contract.get("source_register"))
    claims = _records(contract.get("claims"))
    chart_panels = _records(contract.get("chart_panels"))
    research_perspectives = _records(contract.get("research_perspectives"))
    unavailable = [
        {
            "claim_id": row.get("claim_id"),
            "provider": row.get("provider"),
            "source_status": row.get("source_status"),
            "data_gap": row.get("data_gap"),
            "caveat": row.get("caveat"),
        }
        for row in claims
        if row.get("claim_kind") == "gap"
        or str(row.get("source_status") or "").lower()
        in {"unavailable", "missing-key", "provider-required", "forbidden/subscription-blocked", "rate-limited", "stale"}
    ]
    validation = contract.get("validation") if isinstance(contract.get("validation"), dict) else {}
    errors = [{"kind": "claim-validation", "issue": issue} for issue in list(validation.get("issues") or [])]
    coverage = contract.get("coverage") if isinstance(contract.get("coverage"), dict) else {}
    comparison = contract.get("comparison") if isinstance(contract.get("comparison"), dict) else {}
    summary = {
        "period": contract.get("period"),
        "runtime_mode": contract.get("runtime_mode"),
        "historical_truth": contract.get("historical_truth"),
        "privacy_scope": contract.get("privacy_scope"),
        "claim_count": len(claims),
        "source_count": len(sources),
        "chart_panel_count": len(chart_panels),
        "research_perspective_count": len(research_perspectives),
        "gap_count": coverage.get("gap_count", 0),
        "source_status": coverage.get("source_status", "unknown"),
        "comparison_summary": comparison.get("summary") or {},
        "claim_validation_passed": bool(validation.get("valid")),
        "non_advisory": True,
    }
    return _envelope(
        "daily_brief",
        contract,
        summary=summary,
        source_status=sources,
        unavailable=unavailable,
        errors=errors,
        caveats=[
            "The rule-based brief is composed only from source-bound claims; missing inputs become explicit gaps.",
            "Changed-since-prior compares captured normalized claims and does not establish causality or real-world resolution.",
            "Private watchlist context and local review notes are excluded from external-AI-safe payloads and deterministic fixtures.",
            "Outputs are research information only, not investment advice, trade approval, order routing, or autonomous action.",
        ],
    )


def build_api_daily_brief_history_payload(
    *, brief_id: str | None = None, compare_to: str | None = None, period: str | None = None, db_path: Any = None,
) -> dict[str, Any]:
    history = build_daily_brief_history_contract(brief_id=brief_id, compare_to=compare_to, period=period, db_path=db_path)
    active = history.get("active_capture") if isinstance(history.get("active_capture"), dict) else {}
    sources = _records(active.get("source_register"))
    captures = _records(history.get("captures"))
    comparison = history.get("comparison") if isinstance(history.get("comparison"), dict) else {}
    return _envelope(
        "daily_brief_history",
        history,
        summary={
            "historical_truth": history.get("historical_truth"),
            "privacy_scope": history.get("privacy_scope"),
            "capture_count": len(captures),
            "active_brief_id": active.get("brief_id"),
            "comparison_summary": comparison.get("summary") or {},
        },
        source_status=sources,
        caveats=[
            "Daily brief history contains only project-captured local observations; uncaptured history is not reconstructed.",
            "Local brief database content and review notes are excluded from source releases and deterministic fixtures.",
        ],
    )



def build_api_research_report_payload(
    *,
    include_runtime: bool = False,
    symbol: str = "AAPL",
    crypto_symbol: str = "BTCUSDT",
) -> dict[str, Any]:
    report = build_research_report_workstation_contract(
        include_runtime=include_runtime,
        symbol=symbol,
        crypto_symbol=crypto_symbol,
    )
    sections = _records(report.get("sections"))
    source_register = _records(report.get("source_register"))
    unavailable = [
        {
            "section_id": row.get("section_id"),
            "status": row.get("source_status"),
            "provider": row.get("provider"),
            "data_gap": row.get("data_gap"),
            "caveat": row.get("caveat"),
        }
        for row in sections
        if row.get("source_status") in {"unavailable", "provider-required", "missing-key"}
        or "unavailable" in str(row.get("data_gap") or "").lower()
    ]
    forbidden = find_forbidden_report_phrases(report)
    errors = [
        {"area": "research_report", "error": "forbidden_advisory_language_detected", "phrases": forbidden}
    ] if forbidden else []
    source_status = [
        {
            "provider": row.get("provider"),
            "source": row.get("source"),
            "source_url": row.get("source_url"),
            "source_status": row.get("source_status"),
            "freshness": row.get("freshness"),
            "fetched_at": row.get("fetched_at"),
            "confidence": row.get("confidence"),
            "caveat": row.get("caveat"),
            "data_gap": row.get("data_gap"),
        }
        for row in source_register
    ]
    summary = {
        **to_json_safe(report.get("summary") or {}),
        "forbidden_language_detected": bool(forbidden),
        "payload_mode": "source-bound-clean-room",
    }
    return _envelope(
        "research_report",
        report,
        summary=summary,
        source_status=source_status,
        unavailable=unavailable,
        errors=errors,
        caveats=[
            "Research report sections are source-bound and non-advisory.",
            "Gold Quant is used as a structure reference only; trade, leverage, and account-action language is rewritten or blocked.",
            "Missing source data remains visible as data gaps instead of invented analysis.",
        ],
    )

def build_api_route_manifest_payload(*, fastapi_available: bool | None = None) -> dict[str, Any]:
    rows = [descriptor.to_dict() for descriptor in API_ROUTE_DESCRIPTORS]
    summary = {
        "route_count": len(rows),
        "fastapi_available": bool(fastapi_available) if fastapi_available is not None else None,
        "base_streamlit_ui_preserved": True,
    }
    return _envelope(
        "api_route_manifest",
        rows,
        summary=summary,
        caveats=[
            "FastAPI is optional and belongs in requirements-api.txt, not the base requirements file.",
            "Research/data routes are read-only; explicit local-private POST/PATCH/DELETE routes are bounded persistence actions and never broker execution.",
        ],
    )


def build_api_runtime_health_payload(
    *,
    fastapi_available: bool | None = None,
    api_base_url: str = "http://127.0.0.1:8000",
    web_base_url: str = "http://127.0.0.1:3000",
    provider_payload: dict[str, Any] | None = None,
    results: Iterable[Any] | None = None,
) -> dict[str, Any]:
    checked_at = _now_iso()
    route_rows = [descriptor.to_dict() for descriptor in API_ROUTE_DESCRIPTORS]
    health_payload = provider_payload or build_api_provider_health_payload(results)
    provider_rows = _records(health_payload.get("data") if isinstance(health_payload, dict) else [])
    provider_summary = dict(health_payload.get("summary") or {}) if isinstance(health_payload, dict) else {}
    unavailable_provider_count = len(
        [
            row
            for row in provider_rows
            if row.get("availability") == "unavailable"
            or str(row.get("status") or row.get("source_status") or "").lower()
            in {"missing-key", "unavailable", "forbidden/subscription-blocked", "provider-required"}
        ]
    )
    optional_backend_ready = bool(fastapi_available) if fastapi_available is not None else None
    route_count = len(route_rows)
    read_route_count = len([row for row in route_rows if row.get("method") == "GET"])
    local_action = "python scripts/start_local_product.py"
    components = [
        {
            "component": "next_web",
            "label": "Next.js commercial web shell",
            "status": "expected-local",
            "source_status": "operator-verified",
            "base_url": web_base_url,
            "checked_at": checked_at,
            "recommended_action": local_action,
            "caveat": "This contract reports local orchestration readiness; it cannot prove the browser process is open unless requested by the UI/runtime probe.",
        },
        {
            "component": "fastapi_runtime",
            "label": "Optional local FastAPI contract API",
            "status": "importable" if optional_backend_ready else "optional-missing",
            "source_status": "available" if optional_backend_ready else "unavailable",
            "base_url": api_base_url,
            "checked_at": checked_at,
            "route_count": route_count,
            "recommended_action": local_action if optional_backend_ready else "python -m pip install -r requirements-api.txt",
            "caveat": "FastAPI remains optional; the Next.js product must show fixture fallback honestly when this process is not reachable.",
        },
        {
            "component": "route_manifest",
            "label": "API route contract registry",
            "status": "available",
            "source_status": "contract-ready",
            "checked_at": checked_at,
            "route_count": route_count,
            "read_route_count": read_route_count,
            "mutation_route_count": route_count - read_route_count,
            "recommended_action": "Keep new UI surfaces backed by API envelopes before adding page-local business logic.",
        },
        {
            "component": "provider_health_ledger",
            "label": "Provider health ledger",
            "status": "available" if provider_rows else "empty",
            "source_status": "evidence-led" if provider_rows else "unavailable",
            "checked_at": checked_at,
            "provider_count": provider_summary.get("provider_count", len(provider_rows)),
            "unavailable_count": unavailable_provider_count,
            "recommended_action": "Add free-first provider keys only when a route explicitly reports missing-key or provider-required.",
            "caveat": "Live provider success is row-level. A reachable API does not upgrade unavailable feeds to live.",
        },
    ]
    unavailable = [row for row in components if row.get("source_status") == "unavailable" or row.get("status") == "optional-missing"]
    summary = {
        "runtime_status": "api-importable" if optional_backend_ready else "api-optional-missing",
        "fastapi_available": optional_backend_ready,
        "api_base_url": api_base_url,
        "web_base_url": web_base_url,
        "route_count": route_count,
        "provider_count": provider_summary.get("provider_count", len(provider_rows)),
        "unavailable_provider_count": unavailable_provider_count,
        "launcher_command": local_action,
        "fixture_fallback_required_when_api_unreachable": True,
        "broker_execution_added": False,
        "hosted_persistence_added": False,
    }
    return _envelope(
        "runtime_health",
        {
            "components": components,
            "route_manifest": route_rows,
            "provider_summary": provider_summary,
            "launcher": {
                "command": local_action,
                "web_url": web_base_url,
                "api_url": api_base_url,
                "env": {
                    "NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL": api_base_url,
                    "GLOBAL_TERMINAL_API_BASE_URL": api_base_url,
                },
                "secrets_in_output": False,
            },
        },
        summary=summary,
        source_status=components,
        unavailable=unavailable,
        caveats=[
            "Runtime health is a local orchestration contract, not an external market-data freshness claim.",
            "Static fixtures remain deterministic fallbacks and must stay visibly labeled when the API is offline.",
            "No broker execution, hosted account system, billing, or paid provider dependency is added by this health surface.",
        ],
    )


def validate_api_payload(payload: Any) -> tuple[bool, list[str]]:
    issues: list[str] = []

    def walk(value: Any, path: str = "$") -> None:
        if _dataframe_like(value) or isinstance(value, DataResult):
            issues.append(f"{path} contains non-API runtime object {type(value).__name__}")
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if _field_is_secret(key) and item not in {None, "[redacted]"}:
                    issues.append(f"{path}.{key} contains an unredacted secret-like value")
                status_value = str(item).lower() if key in {"status", "source_status", "freshness_status"} else ""
                if status_value in LIVE_STATUS_VALUES:
                    if not any(value.get(field) for field in ["fetched_at", "latest_fetched_at", "generated_at", "captured_at", "observed_at"]):
                        issues.append(f"{path} claims {item} without fetched_at/latest_fetched_at/captured_at metadata")
                walk(item, f"{path}.{key}")
            return
        if isinstance(value, list):
            for idx, item in enumerate(value):
                walk(item, f"{path}[{idx}]")
            return
        if isinstance(value, (datetime, date)):
            issues.append(f"{path} contains raw datetime/date")

    try:
        import json

        json.dumps(payload)
    except TypeError as exc:
        issues.append(f"payload is not JSON serializable: {exc}")
    walk(payload)
    return not issues, issues
