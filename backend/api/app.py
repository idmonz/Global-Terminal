from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

from lib.env_loader import load_project_env

load_project_env()

from lib.api_contracts import (
    build_api_account_preference_payload,
    build_api_attention_action_payload,
    build_api_attention_desk_payload,
    build_api_tenant_research_desk_payload,
    build_api_account_workspace_payload,
    build_api_analyst_workspace_payload,
    build_api_ai_provider_payload,
    build_api_asset_universe_payload,
    build_api_command_workspace_payload,
    build_api_crypto_intelligence_payload,
    build_api_daily_brief_history_payload,
    build_api_daily_brief_payload,
    build_api_equity_intelligence_payload,
    build_api_event_asset_graph_payload,
    build_api_feed_registry_payload,
    build_api_financial_fundamentals_payload,
    build_api_hosted_scheduler_operations_payload,
    build_api_layer_runtime_payload,
    build_api_map_news_event_fusion_payload,
    build_api_market_map_screener_payload,
    build_api_market_intelligence_payload,
    build_api_news_dashboard_payload,
    build_api_options_quant_payload,
    build_api_observation_run_payload,
    build_api_watchlist_alert_manager_payload,
    build_api_portfolio_risk_payload,
    build_api_product_parity_payload,
    build_api_provider_health_payload,
    build_api_research_operations_payload,
    build_api_research_refresh_job_payload,
    build_api_route_manifest_payload,
    build_api_runtime_health_payload,
    build_api_screener_drilldown_payload,
    build_api_symbol_directory_payload,
    build_api_symbol_delivery_payload,
    build_api_symbol_workstation_payload,
    build_api_watchlist_desk_payload,
    build_api_watchlist_change_payload,
    build_api_research_report_payload,
    build_api_research_memory_payload,
    build_api_war_room_payload,
    build_api_war_room_map_payload,
    build_api_war_room_map_replay_payload,
)
from lib.attention_desk import (
    AttentionConflict,
    AttentionReviewStore,
    build_attention_desk_from_payloads,
)
from lib.account_continuity import AccountContinuityCoordinator
from lib.data_status import get_recent_results
from lib.provider_health_engine import build_provider_health_ledger
from lib.identity_tenancy import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    LocalRateLimiter,
    PreferenceConflict,
    SQLiteTenantPreferenceAdapter,
    SessionManager,
    local_auth_enabled,
    validate_preference_body,
    validate_return_to,
)
from lib.research_operations import (
    build_observed_provider_health,
    build_refresh_request,
    configured_provider_names,
    get_default_operations_store,
    get_research_refresh_job,
    record_panel_delivery_observations,
    submit_exact_refresh,
)
from lib.tenant_research_desk import TenantResearchConflict, TenantResearchDeskStore
from lib.tenant_research_persistence import (
    SQLiteTenantResearchPersistence,
    SupabaseTenantResearchPersistence,
    TenantResearchRepository,
)
from lib.tenant_research_sync import TenantResearchSyncCoordinator
from lib.watchlist_observation_runs import (
    ObservationRunBusy,
    ObservationRunConflict,
    ObservationRunCoordinator,
    ObservationRunStore,
    build_fixture_observation_context,
)
from lib.watchlist_alert_manager import (
    AlertManagerConflict,
    WatchlistAlertManagerStore,
    build_watchlist_alert_manager_contract,
    run_alert_worker_once,
)
from lib.hosted_scheduler_operations import (
    HostedSchedulerConflict,
    HostedSchedulerStore,
    merge_hosted_scheduler_repository_rows,
)
from lib.supabase_hosted_scheduler import SupabaseHostedSchedulerRepository
from lib.supabase_account_runtime import (
    SupabaseAccountConfig,
    SupabaseAuthenticationError,
    SupabaseAuthClient,
    SupabaseHostedSessionManager,
    SupabaseRepositoryUnavailable,
    hosted_auth_enabled,
)

try:
    from fastapi import Body, FastAPI, HTTPException, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
except Exception:  # pragma: no cover - exercised when optional dependency is absent
    FastAPI = None
    Body = None
    HTTPException = None
    Request = None
    Response = None
    CORSMiddleware = None


FASTAPI_AVAILABLE = FastAPI is not None


_IDENTITY_SESSION_MANAGER = SessionManager(
    ttl_seconds=int(os.getenv("GLOBAL_TERMINAL_SESSION_TTL_SECONDS", "3600") or 3600)
)
_IDENTITY_PREFERENCE_ADAPTER = SQLiteTenantPreferenceAdapter(
    os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or None
)
_IDENTITY_RATE_LIMITER = LocalRateLimiter()
_SUPABASE_ACCOUNT_CONFIG = SupabaseAccountConfig.from_env()
_HOSTED_AUTH_CLIENT = SupabaseAuthClient(_SUPABASE_ACCOUNT_CONFIG)
_HOSTED_SESSION_MANAGER = SupabaseHostedSessionManager(_HOSTED_AUTH_CLIENT)
_TENANT_RESEARCH_REPOSITORY: TenantResearchRepository = TenantResearchDeskStore(
    account_db_path=os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or None,
    local_db_path=os.getenv("RESEARCH_WORKSPACE_DB_PATH") or None,
)
_TENANT_RESEARCH_PERSISTENCE = SQLiteTenantResearchPersistence(_TENANT_RESEARCH_REPOSITORY)
_TENANT_RESEARCH_SYNC = TenantResearchSyncCoordinator(
    db_path=os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or None,
    local=_TENANT_RESEARCH_PERSISTENCE,
    hosted=SupabaseTenantResearchPersistence(),
)
_ATTENTION_REVIEW_STORE = AttentionReviewStore(
    os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or None
)
_OBSERVATION_RUN_STORE = ObservationRunStore(
    os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or None
)
_OBSERVATION_RUN_COORDINATOR = ObservationRunCoordinator(
    _OBSERVATION_RUN_STORE,
    lambda context, resource_id: _TENANT_RESEARCH_REPOSITORY.get_watchlist(context, resource_id),
    completion_callback=lambda context, result: _sync_account_continuity(
        context,
        "observation-complete",
        {
            "run_id": result.get("run_id"),
            "status": result.get("status"),
            "version": result.get("version"),
        },
    ),
)
_ALERT_MANAGER_STORE = WatchlistAlertManagerStore(
    os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or None
)
_HOSTED_SCHEDULER_STORE = HostedSchedulerStore(
    os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or None
)
_HOSTED_SCHEDULER_REPOSITORY = SupabaseHostedSchedulerRepository()
_ACCOUNT_CONTINUITY = AccountContinuityCoordinator(
    os.getenv("GLOBAL_TERMINAL_ACCOUNT_DB_PATH") or None
)


def reset_identity_runtime_for_tests(db_path: str | os.PathLike[str] | None = None) -> None:
    global _IDENTITY_SESSION_MANAGER, _IDENTITY_PREFERENCE_ADAPTER, _IDENTITY_RATE_LIMITER
    global _TENANT_RESEARCH_REPOSITORY, _TENANT_RESEARCH_PERSISTENCE, _TENANT_RESEARCH_SYNC
    global _ATTENTION_REVIEW_STORE, _OBSERVATION_RUN_STORE, _OBSERVATION_RUN_COORDINATOR, _ALERT_MANAGER_STORE, _HOSTED_SCHEDULER_STORE, _HOSTED_SCHEDULER_REPOSITORY
    global _SUPABASE_ACCOUNT_CONFIG, _HOSTED_AUTH_CLIENT, _HOSTED_SESSION_MANAGER, _ACCOUNT_CONTINUITY
    _IDENTITY_SESSION_MANAGER = SessionManager(ttl_seconds=3600)
    _IDENTITY_PREFERENCE_ADAPTER = SQLiteTenantPreferenceAdapter(db_path)
    _IDENTITY_RATE_LIMITER = LocalRateLimiter()
    _TENANT_RESEARCH_REPOSITORY = TenantResearchDeskStore(
        account_db_path=db_path,
        local_db_path=os.getenv("RESEARCH_WORKSPACE_DB_PATH") or None,
    )
    _TENANT_RESEARCH_PERSISTENCE = SQLiteTenantResearchPersistence(_TENANT_RESEARCH_REPOSITORY)
    _TENANT_RESEARCH_SYNC = TenantResearchSyncCoordinator(
        db_path=db_path,
        local=_TENANT_RESEARCH_PERSISTENCE,
        hosted=SupabaseTenantResearchPersistence(),
    )
    _ATTENTION_REVIEW_STORE = AttentionReviewStore(db_path)
    _OBSERVATION_RUN_STORE = ObservationRunStore(db_path)
    _OBSERVATION_RUN_COORDINATOR = ObservationRunCoordinator(
        _OBSERVATION_RUN_STORE,
        lambda context, resource_id: _TENANT_RESEARCH_REPOSITORY.get_watchlist(context, resource_id),
        completion_callback=lambda context, result: _sync_account_continuity(
            context,
            "observation-complete",
            {
                "run_id": result.get("run_id"),
                "status": result.get("status"),
                "version": result.get("version"),
            },
        ),
    )
    _ALERT_MANAGER_STORE = WatchlistAlertManagerStore(db_path)
    _HOSTED_SCHEDULER_STORE = HostedSchedulerStore(db_path)
    _HOSTED_SCHEDULER_REPOSITORY = SupabaseHostedSchedulerRepository()
    _SUPABASE_ACCOUNT_CONFIG = SupabaseAccountConfig.from_env()
    _HOSTED_AUTH_CLIENT = SupabaseAuthClient(_SUPABASE_ACCOUNT_CONFIG)
    _HOSTED_SESSION_MANAGER = SupabaseHostedSessionManager(_HOSTED_AUTH_CLIENT)
    _ACCOUNT_CONTINUITY = AccountContinuityCoordinator(db_path)


def configure_hosted_account_runtime_for_tests(
    session_manager: Any,
    continuity: Any,
) -> None:
    global _HOSTED_SESSION_MANAGER, _ACCOUNT_CONTINUITY
    _HOSTED_SESSION_MANAGER = session_manager
    _ACCOUNT_CONTINUITY = continuity


def reset_observation_runtime_for_tests(
    db_path: str | os.PathLike[str] | None = None,
    *,
    adapter: Any | None = None,
    execute_inline: bool = True,
) -> None:
    global _OBSERVATION_RUN_STORE, _OBSERVATION_RUN_COORDINATOR
    _OBSERVATION_RUN_STORE = ObservationRunStore(db_path)
    _OBSERVATION_RUN_COORDINATOR = ObservationRunCoordinator(
        _OBSERVATION_RUN_STORE,
        lambda context, resource_id: _TENANT_RESEARCH_REPOSITORY.get_watchlist(context, resource_id),
        adapter=adapter,
        execute_inline=execute_inline,
        completion_callback=lambda context, result: _sync_account_continuity(
            context,
            "observation-complete",
            {
                "run_id": result.get("run_id"),
                "status": result.get("status"),
                "version": result.get("version"),
            },
        ),
    )


def reset_alert_manager_runtime_for_tests(
    db_path: str | os.PathLike[str] | None = None,
) -> None:
    global _ALERT_MANAGER_STORE
    _ALERT_MANAGER_STORE = WatchlistAlertManagerStore(db_path)


def reset_hosted_scheduler_runtime_for_tests(
    db_path: str | os.PathLike[str] | None = None,
    *,
    repository: Any | None = None,
) -> None:
    global _HOSTED_SCHEDULER_STORE, _HOSTED_SCHEDULER_REPOSITORY
    _HOSTED_SCHEDULER_STORE = HostedSchedulerStore(db_path)
    _HOSTED_SCHEDULER_REPOSITORY = repository or SupabaseHostedSchedulerRepository()


def _account_context(request: Any) -> dict[str, Any]:
    token = request.cookies.get(SESSION_COOKIE)
    hosted = _HOSTED_SESSION_MANAGER.resolve(token)
    if hosted.get("authenticated"):
        return hosted
    return _IDENTITY_SESSION_MANAGER.resolve(token)


def _hosted_context(context: dict[str, Any]) -> bool:
    return bool(context.get("authenticated") and context.get("identity_provider") == "supabase")


def _account_persistence(context: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if _hosted_context(context):
        status = _ACCOUNT_CONTINUITY.status(context)
        repository = dict(status.get("repository") or {})
        repository.update(
            {
                "state": status.get("state"),
                "pending_count": status.get("pending_count"),
                "conflict_count": status.get("conflict_count"),
                "last_restore_at": status.get("last_restore_at"),
                "last_sync_at": status.get("last_sync_at"),
                "last_recovery_at": status.get("last_recovery_at"),
                "last_failure_at": status.get("last_failure_at"),
            }
        )
        return str(status.get("state") or "hosted-unavailable"), repository
    return ("local-test" if context.get("authenticated") else "local"), {}


def _sync_account_continuity(
    context: dict[str, Any],
    operation: str,
    evidence: Any,
) -> dict[str, Any]:
    if not _hosted_context(context):
        return {"status": "local-only", "remote_contacted": False, "provider_call_count": 0}
    digest = hashlib.sha256(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24]
    safe_operation = re.sub(r"[^a-z0-9-]+", "-", str(operation).lower()).strip("-")[:40] or "mutation"
    try:
        return _ACCOUNT_CONTINUITY.sync(
            context,
            idempotency_key=f"phase6p:{safe_operation}:{digest}",
        )
    except Exception:
        # A hosted persistence defect must not roll back a completed local
        # account mutation. The public error is intentionally bounded.
        return {
            "status": "degraded-local-retained",
            "remote_contacted": False,
            "provider_call_count": 0,
            "error_code": "continuity-sync-failed",
        }


def _with_account_continuity(
    data: dict[str, Any],
    context: dict[str, Any],
    operation: str,
    evidence: Any,
) -> dict[str, Any]:
    output = dict(data)
    persistence = _sync_account_continuity(context, operation, evidence)
    output["persistence"] = persistence
    summary = output.get("summary")
    if isinstance(summary, dict):
        output["summary"] = {
            **summary,
            "persistence_status": str(persistence.get("status") or "unknown"),
        }
    return output


def _same_origin(request: Any) -> bool:
    origin = str(request.headers.get("origin") or "").rstrip("/")
    expected = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    return bool(origin and hmac.compare_digest(origin, expected))


def _account_response(payload: dict[str, Any], *, status_code: int = 200):
    return Response(
        content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        status_code=status_code,
        media_type="application/json",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
        },
    )


_PANEL_RESPONSE_CACHE_TTL_SECONDS = 5.0
_PANEL_RESPONSE_CACHE_MAX_ENTRIES = 64
_PANEL_RESPONSE_CACHE: dict[tuple[str, ...], tuple[float, dict[str, Any]]] = {}
_PANEL_RESPONSE_CACHE_LOCK = threading.Lock()


_ETAG_VOLATILE_FIELDS = {
    "age_seconds",
    "generated_at",
    "observation_age_seconds",
    "retrieved_age_seconds",
}


def _panel_response_cache_key(
    *,
    symbol: str,
    panel: str,
    asset_class: str | None,
    interval: str,
    range_name: str,
    chart_type: str,
    compare: str | None,
) -> tuple[str, ...]:
    return (
        symbol.strip().upper(),
        panel.strip().lower(),
        (asset_class or "").strip().lower(),
        interval.strip().lower(),
        range_name.strip().lower(),
        chart_type.strip().lower(),
        (compare or "").strip().upper(),
    )


def _get_cached_panel_response(key: tuple[str, ...]) -> dict[str, Any] | None:
    now = time.monotonic()
    with _PANEL_RESPONSE_CACHE_LOCK:
        cached = _PANEL_RESPONSE_CACHE.get(key)
        if not cached:
            return None
        expires_at, payload = cached
        if expires_at <= now:
            _PANEL_RESPONSE_CACHE.pop(key, None)
            return None
        return payload


def _store_cached_panel_response(
    key: tuple[str, ...],
    payload: dict[str, Any],
) -> None:
    with _PANEL_RESPONSE_CACHE_LOCK:
        if len(_PANEL_RESPONSE_CACHE) >= _PANEL_RESPONSE_CACHE_MAX_ENTRIES:
            oldest = next(iter(_PANEL_RESPONSE_CACHE), None)
            if oldest is not None:
                _PANEL_RESPONSE_CACHE.pop(oldest, None)
        _PANEL_RESPONSE_CACHE[key] = (
            time.monotonic() + _PANEL_RESPONSE_CACHE_TTL_SECONDS,
            payload,
        )


def _invalidate_panel_response_cache(symbol: str) -> None:
    canonical = symbol.strip().upper()
    with _PANEL_RESPONSE_CACHE_LOCK:
        for key in [
            current for current in _PANEL_RESPONSE_CACHE if current[0] == canonical
        ]:
            _PANEL_RESPONSE_CACHE.pop(key, None)


def _stable_etag_basis(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _stable_etag_basis(item)
            for key, item in value.items()
            if key not in _ETAG_VOLATILE_FIELDS
        }
    if isinstance(value, list):
        return [_stable_etag_basis(item) for item in value]
    return value


def _stable_payload_etag(payload: dict[str, Any]) -> str:
    basis = _stable_etag_basis(payload)
    encoded = json.dumps(
        basis,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _symbol_payload_response(
    request: Any,
    payload: dict[str, Any],
    *,
    status_code: int = 200,
):
    etag = f'"{_stable_payload_etag(payload)}"'
    headers = {
        "Cache-Control": "private, max-age=30, stale-while-revalidate=300",
        "ETag": etag,
        "X-Symbol-Workstation-Status": str(payload.get("summary", {}).get("status") or "unavailable"),
    }
    if status_code == 200 and request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(
        content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        status_code=status_code,
        media_type="application/json",
        headers=headers,
    )


def _private_payload_response(request: Any, payload: dict[str, Any], *, status_header: str):
    etag = f'"{_stable_payload_etag(payload)}"'
    headers = {
        "Cache-Control": "private, max-age=30, stale-while-revalidate=300",
        "ETag": etag,
        "X-Global-Terminal-Status": status_header,
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(
        content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        media_type="application/json",
        headers=headers,
    )


def get_api_manifest() -> dict[str, Any]:
    return build_api_route_manifest_payload(fastapi_available=FASTAPI_AVAILABLE)


def get_runtime_health_payload() -> dict[str, Any]:
    return build_api_runtime_health_payload(
        fastapi_available=FASTAPI_AVAILABLE,
        provider_payload=get_provider_health_payload(),
    )


def get_feeds_payload() -> dict[str, Any]:
    return build_api_feed_registry_payload()


def get_product_parity_payload() -> dict[str, Any]:
    return build_api_product_parity_payload()


def get_market_intelligence_payload(*, include_runtime: bool = False) -> dict[str, Any]:
    return build_api_market_intelligence_payload(include_runtime=include_runtime)


def get_equity_intelligence_payload(symbol: str = "AAPL", *, include_runtime: bool = False) -> dict[str, Any]:
    return build_api_equity_intelligence_payload(symbol=symbol, include_runtime=include_runtime)


def get_financial_fundamentals_payload(symbol: str = "AAPL", *, include_runtime: bool = False) -> dict[str, Any]:
    return build_api_financial_fundamentals_payload(symbol=symbol, include_runtime=include_runtime)


def get_options_quant_payload(symbol: str = "AAPL", *, expiry: str | None = None, include_runtime: bool = False) -> dict[str, Any]:
    return build_api_options_quant_payload(symbol=symbol, expiry=expiry, include_runtime=include_runtime)


def get_portfolio_risk_payload(
    *,
    portfolio_id: str = "demo-core",
    period: str = "1y",
    benchmark: str = "SPY",
    include_runtime: bool = False,
) -> dict[str, Any]:
    return build_api_portfolio_risk_payload(
        portfolio_id=portfolio_id,
        period=period,
        benchmark=benchmark,
        include_runtime=include_runtime,
    )


def get_screener_drilldown_payload(*, include_runtime: bool = False) -> dict[str, Any]:
    return build_api_screener_drilldown_payload(include_runtime=include_runtime)


def get_market_map_screener_payload(*, include_runtime: bool = False, period: str = "3mo") -> dict[str, Any]:
    return build_api_market_map_screener_payload(include_runtime=include_runtime, period=period)


def get_crypto_intelligence_payload(symbol: str = "BTCUSDT", *, include_runtime: bool = False) -> dict[str, Any]:
    return build_api_crypto_intelligence_payload(symbol=symbol, include_runtime=include_runtime)


def get_symbol_directory_payload(
    *,
    query: str = "",
    asset_class: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    return build_api_symbol_directory_payload(query=query, asset_class=asset_class, limit=limit)


def get_symbol_workstation_payload(
    *,
    symbol: str = "AAPL",
    asset_class: str | None = None,
    interval: str = "1d",
    range_name: str = "3mo",
    runtime_mode: str = "fixture",
    chart_type: str = "candlestick",
    panels: str | None = None,
    compare: str | None = None,
) -> dict[str, Any]:
    return build_api_symbol_workstation_payload(
        symbol=symbol,
        asset_class=asset_class,
        interval=interval,
        range_name=range_name,
        runtime_mode=runtime_mode,
        chart_type=chart_type,
        panels=panels,
        compare=compare,
    )


def get_symbol_delivery_payload(
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
    return build_api_symbol_delivery_payload(
        symbol=symbol,
        delivery=delivery,
        asset_class=asset_class,
        interval=interval,
        range_name=range_name,
        runtime_mode=runtime_mode,
        chart_type=chart_type,
        compare=compare,
    )


def get_analyst_workspace_payload(
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
    return build_api_analyst_workspace_payload(
        symbol=symbol,
        asset_class=asset_class,
        interval=interval,
        range_name=range_name,
        runtime_mode=runtime_mode,
        compare=compare,
        layout=layout,
        return_state=return_state,
        change_context=change_context,
    )


def get_watchlist_desk_payload(
    *,
    mode: str = "fixture",
    list_id: str = "primary",
    selected: str | None = None,
) -> dict[str, Any]:
    return build_api_watchlist_desk_payload(
        mode=mode,
        list_id=list_id,
        selected_symbol=selected,
    )


def get_watchlist_change_payload(*, mode: str = "local", list_id: str = "primary") -> dict[str, Any]:
    return build_api_watchlist_change_payload(mode=mode, list_id=list_id)


def _load_static_fixture_payload(name: str) -> dict[str, Any]:
    safe_name = re.sub(r"[^a-z0-9-]", "", str(name or "").lower())
    if not safe_name:
        return {}
    target = Path(__file__).resolve().parents[2] / "static" / "api-fixtures" / f"{safe_name}.json"
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def get_attention_desk_payload(
    *,
    mode: str = "cache",
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = str(mode or "cache").strip().lower()
    if normalized not in {"fixture", "cache", "local"}:
        raise ValueError("Attention Desk mode must be fixture, cache, or local.")
    if normalized == "fixture":
        watchlist_payload = _load_static_fixture_payload("watchlist-desk")
        daily_brief_payload = _load_static_fixture_payload("daily-brief")
        news_payload = _load_static_fixture_payload("news")
        provider_payload = _load_static_fixture_payload("provider-health")
        war_map_payload = _load_static_fixture_payload("map-news-event-fusion")
    else:
        watchlist_payload = get_watchlist_desk_payload(mode="local")
        daily_brief_payload = get_daily_brief_payload(mode="cache")
        news_payload = get_news_payload(include_runtime=False)
        provider_payload = get_provider_health_payload()
        war_map_payload = get_map_news_event_fusion_payload(include_runtime=False)
    source_kwargs = {
        "watchlist_payload": watchlist_payload,
        "daily_brief_payload": daily_brief_payload,
        "news_payload": news_payload,
        "provider_health_payload": provider_payload,
        "war_map_payload": war_map_payload,
        "mode": "fixture" if normalized == "fixture" else "cache",
        "observation_run": (
            build_fixture_observation_context()
            if normalized == "fixture"
            else _OBSERVATION_RUN_STORE.build_attention_context(context)
            if context and context.get("authenticated")
            else None
        ),
    }
    base = build_attention_desk_from_payloads(**source_kwargs)
    if context and context.get("authenticated"):
        fingerprints = [
            str(row.get("fingerprint") or "")
            for row in base.get("all_items") or []
            if isinstance(row, dict) and row.get("fingerprint")
        ]
        base = build_attention_desk_from_payloads(
            **source_kwargs,
            review_states=_ATTENTION_REVIEW_STORE.list_states(context, fingerprints),
            policy=_ATTENTION_REVIEW_STORE.get_policy(context),
            checkpoint=_ATTENTION_REVIEW_STORE.get_checkpoint(context),
        )
    return build_api_attention_desk_payload(base)


def get_provider_health_payload() -> dict[str, Any]:
    memory_rows = build_provider_health_ledger(get_recent_results())
    observed_rows = build_observed_provider_health(
        get_default_operations_store().list_panel_observations(),
        configured_providers=configured_provider_names(),
    )
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for row in [*memory_rows, *observed_rows]:
        key = (
            str(row.get("provider") or ""),
            str(row.get("source") or row.get("panel") or ""),
        )
        merged[key] = row
    return build_api_provider_health_payload(ledger=list(merged.values()))


def get_research_operations_payload(
    *,
    symbol: str,
    asset_class: str = "equity",
    interval: str = "1d",
    range_name: str = "3mo",
    panels: list[str] | None = None,
) -> dict[str, Any]:
    request = build_refresh_request(
        symbol,
        asset_class=asset_class,
        interval=interval,
        range_name=range_name,
        panels=panels,
        idempotency_key="operations-read",
    )
    return build_api_research_operations_payload(
        request,
        store=get_default_operations_store(),
    )


def get_layers_payload(*, include_runtime: bool = False) -> dict[str, Any]:
    if not include_runtime:
        return build_api_layer_runtime_payload()
    from lib.live_feeds import build_keyless_runtime_feeds

    runtime = build_keyless_runtime_feeds()
    statuses = runtime.get("source_statuses") or runtime.get("source_status") or []
    return build_api_layer_runtime_payload(runtime_feeds=runtime, statuses=statuses)


def get_news_payload(*, include_runtime: bool = False, query: str = "geopolitical risk OR oil OR macro OR crypto") -> dict[str, Any]:
    if not include_runtime:
        return build_api_news_dashboard_payload(statuses=get_recent_results())
    from lib.live_feeds import fetch_live_news_feed

    rows, status = fetch_live_news_feed(query=query)
    return build_api_news_dashboard_payload(rows, [status])


def get_war_room_payload(*, include_runtime: bool = False, max_events: int = 100) -> dict[str, Any]:
    return build_api_war_room_payload(include_default_runtime=include_runtime, max_events=max_events)


def get_ai_providers_payload(*, preferred: str = "auto") -> dict[str, Any]:
    return build_api_ai_provider_payload(preferred=preferred)


def get_asset_universe_payload() -> dict[str, Any]:
    return build_api_asset_universe_payload()


def get_event_asset_graph_payload(*, include_runtime: bool = False) -> dict[str, Any]:
    war_room_payload = get_war_room_payload(include_runtime=include_runtime)
    provider_payload = get_provider_health_payload()
    return build_api_event_asset_graph_payload(
        events=(war_room_payload.get("data") or {}).get("events"),
        provider_rows=provider_payload.get("data"),
        asset_universe=(get_asset_universe_payload().get("data") or {}),
    )


def get_command_workspace_payload(*, include_runtime: bool = False) -> dict[str, Any]:
    event_graph_payload = get_event_asset_graph_payload(include_runtime=include_runtime)
    provider_payload = get_provider_health_payload()
    return build_api_command_workspace_payload(
        event_graph=(event_graph_payload.get("data") or {}),
        provider_rows=provider_payload.get("data"),
    )


def get_war_room_map_payload(*, include_runtime: bool = False) -> dict[str, Any]:
    war_room_payload = get_war_room_payload(include_runtime=include_runtime, max_events=400)
    provider_payload = get_provider_health_payload()
    event_graph_payload = get_event_asset_graph_payload(include_runtime=include_runtime)
    war_room_data = war_room_payload.get("data") or {}
    return build_api_war_room_map_payload(
        events=war_room_data.get("events"),
        layer_runtime=war_room_data.get("layer_runtime_status"),
        provider_rows=provider_payload.get("data"),
        event_graph=event_graph_payload.get("data") or {},
    )


def get_map_news_event_fusion_payload(*, include_runtime: bool = False) -> dict[str, Any]:
    war_room_map_payload = get_war_room_map_payload(include_runtime=include_runtime)
    news_payload = get_news_payload(include_runtime=include_runtime)
    event_graph_payload = get_event_asset_graph_payload(include_runtime=include_runtime)
    provider_payload = get_provider_health_payload()
    layer_payload = get_layers_payload(include_runtime=include_runtime)
    market_payload = get_market_intelligence_payload(include_runtime=include_runtime)
    return build_api_map_news_event_fusion_payload(
        war_room_map=war_room_map_payload.get("data") or {},
        news_dashboard=news_payload.get("data") or {},
        event_graph=event_graph_payload.get("data") or {},
        provider_health=provider_payload,
        layer_runtime=layer_payload.get("data") or {},
        market_intelligence=market_payload.get("data") or {},
    )


def get_war_room_map_replay_payload(
    *,
    snapshot_id: str | None = None,
    compare_to: str | None = None,
    db_path: Any = None,
) -> dict[str, Any]:
    return build_api_war_room_map_replay_payload(
        snapshot_id=snapshot_id,
        compare_to=compare_to,
        db_path=db_path,
    )


def capture_war_room_map_replay_payload(
    *,
    runtime_mode: str = "cache",
    retention_days: int = 30,
    db_path: Any = None,
) -> dict[str, Any]:
    from lib.war_room_map_replay import capture_war_room_map_snapshot

    mode = str(runtime_mode or "cache").strip().lower()
    if mode not in {"cache", "live-if-available"}:
        raise ValueError("Map snapshot capture accepts cache or live-if-available mode only.")
    current = get_map_news_event_fusion_payload(include_runtime=True)
    captured = capture_war_room_map_snapshot(
        current,
        runtime_mode=mode,
        retention_days=retention_days,
        db_path=db_path,
    )
    envelope = get_war_room_map_replay_payload(snapshot_id=str(captured["snapshot_id"]), db_path=db_path)
    if isinstance(envelope.get("data"), dict):
        envelope["data"]["capture_result"] = captured
    if isinstance(envelope.get("summary"), dict):
        envelope["summary"]["capture_created"] = captured["created"]
        envelope["summary"]["capture_deduplicated"] = captured["deduplicated"]
    return envelope



def get_research_report_payload(
    *,
    include_runtime: bool = False,
    symbol: str = "AAPL",
    crypto_symbol: str = "BTCUSDT",
) -> dict[str, Any]:
    return build_api_research_report_payload(
        include_runtime=include_runtime,
        symbol=symbol,
        crypto_symbol=crypto_symbol,
    )


def get_research_memory_payload(
    *,
    mode: str = "demo",
    collection_id: str = "demo-research",
    surface: str = "inbox",
    memory_type: str = "",
    tag: str = "",
    db_path: Any = None,
) -> dict[str, Any]:
    return build_api_research_memory_payload(
        mode=mode,
        collection_id=collection_id,
        surface=surface,
        memory_type=memory_type,
        tag=tag,
        db_path=db_path,
    )


def get_daily_brief_payload(
    *, mode: str = "cache", period: str = "morning", db_path: Any = None,
) -> dict[str, Any]:
    normalized = str(mode or "cache").strip().lower()
    if normalized not in {"fixture", "cache", "live-if-available", "local"}:
        raise ValueError("Invalid daily brief mode.")
    return build_api_daily_brief_payload(
        period=period,
        include_runtime=normalized == "live-if-available",
        db_path=db_path,
        demo=normalized == "fixture",
    )


def capture_daily_brief_payload(
    *, mode: str = "cache", period: str = "morning", retention_days: int = 90, db_path: Any = None,
) -> dict[str, Any]:
    from lib.daily_briefing import capture_daily_brief

    envelope = get_daily_brief_payload(mode=mode, period=period, db_path=db_path)
    captured = capture_daily_brief(envelope.get("data") or {}, retention_days=retention_days, db_path=db_path)
    return {
        "ok": True,
        "privacy_scope": "local-private",
        "capture": captured,
        "brief": envelope,
    }

def create_app():
    if FastAPI is None:
        return None
    app = FastAPI(
        title="Global Market Terminal API",
        version="0.2b",
        description="Optional local API-ready contracts for the Global Terminal runtime.",
    )
    if CORSMiddleware is not None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
            allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):3[0-9]{3}$",
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Content-Type"],
        )

    @app.get("/api")
    def manifest() -> dict[str, Any]:
        return get_api_manifest()

    @app.get("/api/attention-desk")
    def attention_desk(mode: str = "cache") -> dict[str, Any]:
        try:
            return get_attention_desk_payload(mode=mode)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/runtime-health")
    def runtime_health() -> dict[str, Any]:
        return get_runtime_health_payload()

    @app.get("/api/feeds")
    def feeds() -> dict[str, Any]:
        return get_feeds_payload()

    @app.get("/api/product-parity")
    def product_parity() -> dict[str, Any]:
        return get_product_parity_payload()

    @app.get("/api/market-intelligence")
    def market_intelligence(include_runtime: bool = False) -> dict[str, Any]:
        return get_market_intelligence_payload(include_runtime=include_runtime)

    @app.get("/api/equity-intelligence")
    def equity_intelligence(symbol: str = "AAPL", include_runtime: bool = False) -> dict[str, Any]:
        return get_equity_intelligence_payload(symbol=symbol, include_runtime=include_runtime)

    @app.get("/api/financial-fundamentals")
    def financial_fundamentals(symbol: str = "AAPL", include_runtime: bool = False) -> dict[str, Any]:
        return get_financial_fundamentals_payload(symbol=symbol, include_runtime=include_runtime)

    @app.get("/api/options-quant")
    def options_quant(symbol: str = "AAPL", expiry: str | None = None, include_runtime: bool = False) -> dict[str, Any]:
        return get_options_quant_payload(symbol=symbol, expiry=expiry, include_runtime=include_runtime)

    @app.get("/api/portfolio-risk")
    def portfolio_risk(
        portfolio: str = "demo-core",
        period: str = "1y",
        benchmark: str = "SPY",
        include_runtime: bool = False,
    ) -> dict[str, Any]:
        return get_portfolio_risk_payload(
            portfolio_id=portfolio,
            period=period,
            benchmark=benchmark,
            include_runtime=include_runtime,
        )

    @app.get("/api/screener-drilldown")
    def screener_drilldown(include_runtime: bool = False) -> dict[str, Any]:
        return get_screener_drilldown_payload(include_runtime=include_runtime)

    @app.get("/api/market-map-screener")
    def market_map_screener(include_runtime: bool = False, period: str = "3mo"):
        payload = get_market_map_screener_payload(include_runtime=include_runtime, period=period)
        return Response(
            content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            media_type="application/json",
        )

    @app.get("/api/market-map-snapshot")
    def market_map_snapshot(request: Request):
        from lib.market_snapshot_store import read_market_snapshot

        try:
            max_age_seconds = max(0, int(os.getenv("MARKET_SNAPSHOT_MAX_AGE_SECONDS", "900")))
        except ValueError:
            max_age_seconds = 900
        payload = read_market_snapshot(max_age_seconds=max_age_seconds)
        materialization = payload.get("data", {}).get("materialization", {})
        etag = f'"{materialization.get("etag")}"' if materialization.get("etag") else None
        headers = {
            "Cache-Control": "public, max-age=30, stale-while-revalidate=300",
            "X-Market-Snapshot-Status": str(materialization.get("read_status") or "unavailable"),
        }
        if etag:
            headers["ETag"] = etag
        if etag and request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(
            content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            media_type="application/json",
            headers=headers,
        )

    @app.get("/api/market-map-snapshot/{symbol}")
    def market_map_snapshot_detail(symbol: str):
        from lib.market_snapshot_store import build_market_snapshot_detail

        payload = build_market_snapshot_detail(symbol)
        return Response(
            content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            media_type="application/json",
            headers={"Cache-Control": "public, max-age=30, stale-while-revalidate=300"},
        )

    @app.get("/api/market-refresh-health")
    def market_refresh_health() -> dict[str, Any]:
        from lib.market_snapshot_store import get_market_refresh_health

        return get_market_refresh_health()

    @app.get("/api/market-refresh-history")
    def market_refresh_history(limit: int = 20) -> dict[str, Any]:
        from lib.market_snapshot_store import get_market_refresh_history

        return get_market_refresh_history(limit=max(1, min(int(limit), 100)))

    @app.get("/api/market-map-screens")
    def market_map_screens() -> dict[str, Any]:
        from lib.saved_market_screens import build_saved_screen_readiness, list_market_screens

        return {
            "ok": True,
            "privacy_scope": "local-private",
            "readiness": build_saved_screen_readiness(),
            "screens": list_market_screens(),
        }

    @app.post("/api/market-map-screens")
    def market_map_screen_create(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.saved_market_screens import save_market_screen

        try:
            screen = save_market_screen(
                str(payload.get("name") or ""),
                dict(payload.get("definition") or {}),
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "screen": screen}

    @app.patch("/api/market-map-screens/{screen_id}")
    def market_map_screen_rename(screen_id: str, payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.saved_market_screens import rename_market_screen

        try:
            screen = rename_market_screen(screen_id, str(payload.get("name") or ""))
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if "not found" in message.lower() else 422
            raise HTTPException(status_code=status_code, detail=message) from exc
        return {"ok": True, "privacy_scope": "local-private", "screen": screen}

    @app.delete("/api/market-map-screens/{screen_id}")
    def market_map_screen_archive(screen_id: str) -> dict[str, Any]:
        from lib.saved_market_screens import archive_market_screen

        try:
            archived = archive_market_screen(screen_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not archived:
            raise HTTPException(status_code=404, detail="Saved screen not found.")
        return {"ok": True, "privacy_scope": "local-private", "screen_id": screen_id}

    @app.get("/api/crypto-intelligence")
    def crypto_intelligence(symbol: str = "BTCUSDT", include_runtime: bool = False) -> dict[str, Any]:
        return get_crypto_intelligence_payload(symbol=symbol, include_runtime=include_runtime)

    @app.get("/api/symbol-directory")
    def symbol_directory(query: str = "", asset_class: str | None = None, limit: int = 20) -> dict[str, Any]:
        return get_symbol_directory_payload(query=query, asset_class=asset_class, limit=limit)

    @app.get("/api/symbol-workstation")
    def symbol_workstation(
        request: Request,
        symbol: str = "AAPL",
        asset_class: str | None = None,
        interval: str = "1d",
        range: str = "3mo",
        runtime_mode: str = "fixture",
        chart_type: str = "candlestick",
        panels: str | None = None,
        compare: str | None = None,
    ):
        payload = get_symbol_workstation_payload(
            symbol=symbol,
            asset_class=asset_class,
            interval=interval,
            range_name=range,
            runtime_mode=runtime_mode,
            chart_type=chart_type,
            panels=panels,
            compare=compare,
        )
        return _symbol_payload_response(request, payload)

    @app.get("/api/symbol-workstation/{symbol}")
    def exact_symbol_workstation(
        request: Request,
        symbol: str,
        asset_class: str | None = None,
        interval: str = "1d",
        range: str = "3mo",
        runtime_mode: str = "fixture",
        chart_type: str = "candlestick",
        panels: str | None = None,
        compare: str | None = None,
    ):
        payload = get_symbol_workstation_payload(
            symbol=symbol,
            asset_class=asset_class,
            interval=interval,
            range_name=range,
            runtime_mode=runtime_mode,
            chart_type=chart_type,
            panels=panels,
            compare=compare,
        )
        status_code = 200 if payload.get("summary", {}).get("workstation_count") == 1 else 404
        return _symbol_payload_response(request, payload, status_code=status_code)

    @app.get("/api/symbol-workstation/{symbol}/summary")
    def exact_symbol_workstation_summary(
        request: Request,
        symbol: str,
        asset_class: str | None = None,
        interval: str = "1d",
        range: str = "3mo",
        runtime_mode: str = "cache",
        chart_type: str = "candlestick",
    ):
        payload = get_symbol_delivery_payload(
            symbol=symbol,
            delivery="summary",
            asset_class=asset_class,
            interval=interval,
            range_name=range,
            runtime_mode=runtime_mode,
            chart_type=chart_type,
        )
        status_code = 200 if payload.get("summary", {}).get("workstation_count") == 1 else 404
        return _symbol_payload_response(request, payload, status_code=status_code)

    @app.get("/api/symbol-workstation/{symbol}/panels/{panel}")
    def exact_symbol_workstation_panel(
        request: Request,
        symbol: str,
        panel: str,
        asset_class: str | None = None,
        interval: str = "1d",
        range: str = "3mo",
        runtime_mode: str = "cache",
        chart_type: str = "candlestick",
        compare: str | None = None,
    ):
        try:
            panel_cache_key = _panel_response_cache_key(
                symbol=symbol,
                panel=panel,
                asset_class=asset_class,
                interval=interval,
                range_name=range,
                chart_type=chart_type,
                compare=compare,
            )
            payload = (
                _get_cached_panel_response(panel_cache_key)
                if runtime_mode == "cache"
                else None
            )
            panel_response_cache_hit = payload is not None
            if payload is None:
                payload = get_symbol_delivery_payload(
                    symbol=symbol,
                    delivery=panel,
                    asset_class=asset_class,
                    interval=interval,
                    range_name=range,
                    runtime_mode=runtime_mode,
                    chart_type=chart_type,
                    compare=compare,
                )
                if runtime_mode == "cache":
                    _store_cached_panel_response(panel_cache_key, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        status_code = 200 if payload.get("summary", {}).get("workstation_count") == 1 else 404
        if (
            status_code == 200
            and runtime_mode != "fixture"
            and not panel_response_cache_hit
        ):
            try:
                payload_data = payload.get("data")
                workstations = (
                    payload_data.get("workstations")
                    if isinstance(payload_data, dict)
                    else None
                )
                first_workstation = (
                    workstations[0]
                    if isinstance(workstations, list)
                    and workstations
                    and isinstance(workstations[0], dict)
                    else {}
                )
                delivered_identity = first_workstation.get("identity")
                resolved_asset_class = (
                    asset_class
                    or (
                        delivered_identity.get("asset_class")
                        if isinstance(delivered_identity, dict)
                        else None
                    )
                    or "equity"
                )
                observation_request = build_refresh_request(
                    symbol,
                    asset_class=resolved_asset_class,
                    interval=interval,
                    range_name=range,
                    panels=[panel],
                    runtime_mode=runtime_mode,
                    idempotency_key="panel-observation",
                )
                record_panel_delivery_observations(
                    get_default_operations_store(),
                    observation_request,
                    panel,
                    payload,
                )
            except Exception:
                # Operational observation must never make a valid research
                # panel unavailable.
                pass
        return _symbol_payload_response(request, payload, status_code=status_code)

    @app.get("/api/analyst-workspace/{symbol}")
    def exact_analyst_workspace(
        request: Request,
        symbol: str,
        asset_class: str | None = None,
        interval: str = "1d",
        range: str = "3mo",
        runtime_mode: str = "cache",
        compare: str | None = None,
        layout: str = "research",
        split: int = 58,
        panel: str = "chart-core",
        origin: str | None = None,
        originState: str | None = None,
        list: str | None = None,
        type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        change: str | None = None,
        change_type: str | None = None,
    ):
        resolved_change = None
        if change and list:
            try:
                if runtime_mode == "fixture":
                    from lib.watchlist_desk import build_watchlist_desk_fixture_contract

                    change_contract = build_watchlist_desk_fixture_contract()
                else:
                    from lib.watchlist_desk import build_watchlist_change_contract

                    change_contract = build_watchlist_change_contract(list)
                inbox = change_contract.get("change_inbox") or {}
                resolved_change = next(
                    (
                        row
                        for row in inbox.get("changes") or []
                        if isinstance(row, dict)
                        and row.get("change_id") == change
                        and str(row.get("symbol") or "").upper() == symbol.upper()
                    ),
                    None,
                )
            except Exception:
                resolved_change = None
        safe_origin_state = (
            originState
            if origin == "attention-desk"
            and isinstance(originState, str)
            and len(originState) <= 512
            and not any(character in originState for character in ("\r", "\n", "\\"))
            else None
        )
        payload = get_analyst_workspace_payload(
            symbol=symbol,
            asset_class=asset_class,
            interval=interval,
            range_name=range,
            runtime_mode=runtime_mode,
            compare=compare,
            layout={
                "preset": layout,
                "split_percent": split,
                "focused_panel": panel,
            },
            return_state={
                "origin": origin,
                "originState": safe_origin_state,
                "list": list,
                "type": type,
                "severity": severity,
                "status": status,
                "change": change,
                "layout": layout,
                "panel": panel,
                "symbol": symbol,
                "interval": interval,
                "range": range,
            },
            change_context=resolved_change or (
                {
                    "change_id": change,
                    "symbol": symbol,
                    "change_type": change_type,
                }
                if change
                else None
            ),
        )
        status_code = (
            200 if payload.get("summary", {}).get("workspace_count") == 1 else 404
        )
        return _symbol_payload_response(request, payload, status_code=status_code)

    @app.get("/api/analyst-workspace/{symbol}/operations")
    def exact_analyst_workspace_operations(
        request: Request,
        symbol: str,
        asset_class: str = "equity",
        interval: str = "1d",
        range: str = "3mo",
        panels: str | None = None,
    ):
        requested_panels = (
            [value.strip() for value in panels.split(",") if value.strip()]
            if panels
            else None
        )
        try:
            workspace = get_analyst_workspace_payload(
                symbol=symbol,
                asset_class=asset_class,
                interval=interval,
                range_name=range,
                runtime_mode="cache",
            )
            if workspace.get("summary", {}).get("workspace_count") != 1:
                raise HTTPException(status_code=404, detail="Unknown exact workspace symbol.")
            payload = get_research_operations_payload(
                symbol=symbol,
                asset_class=asset_class,
                interval=interval,
                range_name=range,
                panels=requested_panels,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _symbol_payload_response(request, payload)

    @app.post("/api/analyst-workspace/{symbol}/refresh")
    def refresh_exact_analyst_workspace(
        symbol: str,
        body: dict[str, Any] = Body(default={}),
    ):
        try:
            request_payload = build_refresh_request(
                symbol,
                asset_class=str(body.get("asset_class") or "equity"),
                interval=str(body.get("interval") or "1d"),
                range_name=str(body.get("range") or "3mo"),
                panels=body.get("panels"),
                runtime_mode="live-if-available",
                idempotency_key=body.get("idempotency_key"),
            )
            _invalidate_panel_response_cache(symbol)
            job = submit_exact_refresh(request_payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        payload = build_api_research_refresh_job_payload(job)
        status_code = 409 if job.get("status") == "overlap" else 202
        return Response(
            content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            status_code=status_code,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/research-operations/jobs/{job_id}")
    def research_refresh_job(request: Request, job_id: str):
        if not re.fullmatch(r"research_refresh_[a-f0-9]{12}", job_id):
            raise HTTPException(status_code=422, detail="Invalid research refresh job id.")
        job = get_research_refresh_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Research refresh job not found.")
        return _symbol_payload_response(
            request,
            build_api_research_refresh_job_payload(job),
        )

    @app.get("/api/account/session")
    def account_session(request: Request):
        context = _account_context(request)
        preference = None
        if context.get("authenticated"):
            preference = _IDENTITY_PREFERENCE_ADAPTER.get(
                context,
                "analyst-layout",
            )
        sync_state, persistence = _account_persistence(context)
        return _account_response(
            build_api_account_workspace_payload(
                context,
                preference=preference,
                sync_state=("saved-local-test" if preference and not _hosted_context(context) else sync_state),
                persistence_health=persistence or None,
            )
        )

    @app.post("/api/account/hosted-session")
    def account_hosted_session(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ):
        if not hosted_auth_enabled(_SUPABASE_ACCOUNT_CONFIG):
            raise HTTPException(status_code=503, detail="Hosted sign-in is unavailable.")
        if not _same_origin(request):
            raise HTTPException(status_code=403, detail="Same-origin request required.")
        if any(key in body for key in ("tenant_id", "user_id", "owner_user_id", "access_token", "refresh_token")):
            raise HTTPException(status_code=422, detail="Account identity is server-derived.")
        client_key = f"hosted-signin:{getattr(request.client, 'host', 'unknown')}"
        if not _IDENTITY_RATE_LIMITER.allow(client_key, limit=5, window_seconds=60):
            raise HTTPException(status_code=429, detail="Sign-in rate limit reached.")
        prior_token = request.cookies.get(SESSION_COOKIE)
        try:
            return_to = validate_return_to(body.get("return_to") or "/")
            credentials = _HOSTED_SESSION_MANAGER.create(
                str(body.get("email") or ""),
                str(body.get("password") or ""),
                replace=prior_token,
            )
            _IDENTITY_SESSION_MANAGER.revoke(prior_token)
            context = _HOSTED_SESSION_MANAGER.resolve(credentials.session_token)
            if not context.get("authenticated"):
                raise SupabaseAuthenticationError(
                    "Hosted sign-in could not be verified.",
                    stage="session-resolution-failed",
                )
            restore = _ACCOUNT_CONTINUITY.restore(context)
            preference = _IDENTITY_PREFERENCE_ADAPTER.get(context, "analyst-layout")
            sync_state, persistence = _account_persistence(context)
        except SupabaseAuthenticationError as exc:
            diagnostic_headers = None
            diagnostic_mode = str(os.getenv("GLOBAL_TERMINAL_QA_AUTH_DIAGNOSTICS", "")).strip().lower()
            client_host = str(getattr(request.client, "host", ""))
            diagnostic_stage = str(getattr(exc, "stage", "auth-unverified"))
            if (
                diagnostic_mode == "phase6p-recovery"
                and client_host in {"127.0.0.1", "::1", "testclient"}
                and re.fullmatch(r"[a-z0-9-]{1,64}", diagnostic_stage)
            ):
                diagnostic_headers = {"X-Global-Terminal-QA-Auth-Stage": diagnostic_stage}
            raise HTTPException(
                status_code=401,
                detail="Hosted sign-in could not be verified.",
                headers=diagnostic_headers,
            ) from exc
        except SupabaseRepositoryUnavailable as exc:
            raise HTTPException(status_code=503, detail="Hosted sign-in is temporarily unavailable.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        payload = build_api_account_workspace_payload(
            context,
            preference=preference,
            sync_state=sync_state,
            persistence_health=persistence,
        )
        payload["data"]["return_to"] = return_to
        payload["data"]["restore"] = restore
        response = _account_response(payload, status_code=201)
        secure = str(os.getenv("GLOBAL_TERMINAL_COOKIE_SECURE", "")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        response.set_cookie(
            SESSION_COOKIE,
            credentials.session_token,
            max_age=_HOSTED_SESSION_MANAGER.ttl_seconds,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )
        response.set_cookie(
            CSRF_COOKIE,
            credentials.csrf_token,
            max_age=_HOSTED_SESSION_MANAGER.ttl_seconds,
            httponly=False,
            secure=secure,
            samesite="strict",
            path="/",
        )
        return response

    @app.post("/api/account/local-session")
    def account_local_session(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ):
        if not local_auth_enabled():
            raise HTTPException(
                status_code=503,
                detail="Process-local test identity is disabled.",
            )
        if not _same_origin(request):
            raise HTTPException(status_code=403, detail="Same-origin request required.")
        client_key = f"signin:{getattr(request.client, 'host', 'unknown')}"
        if not _IDENTITY_RATE_LIMITER.allow(
            client_key,
            limit=5,
            window_seconds=60,
        ):
            raise HTTPException(status_code=429, detail="Sign-in rate limit reached.")
        try:
            return_to = validate_return_to(body.get("return_to") or "/")
            _HOSTED_SESSION_MANAGER.revoke(request.cookies.get(SESSION_COOKIE))
            credentials = _IDENTITY_SESSION_MANAGER.create(
                str(body.get("alias") or ""),
                replace=request.cookies.get(SESSION_COOKIE),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        context = _IDENTITY_SESSION_MANAGER.resolve(credentials.session_token)
        payload = build_api_account_workspace_payload(context, sync_state="local-test")
        payload["data"]["return_to"] = return_to
        response = _account_response(payload, status_code=201)
        secure = str(os.getenv("GLOBAL_TERMINAL_COOKIE_SECURE", "")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        max_age = _IDENTITY_SESSION_MANAGER.ttl_seconds
        response.set_cookie(
            SESSION_COOKIE,
            credentials.session_token,
            max_age=max_age,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )
        response.set_cookie(
            CSRF_COOKIE,
            credentials.csrf_token,
            max_age=max_age,
            httponly=False,
            secure=secure,
            samesite="strict",
            path="/",
        )
        return response

    def require_account_mutation(request: Request) -> dict[str, Any]:
        if not _same_origin(request):
            raise HTTPException(status_code=403, detail="Same-origin request required.")
        session_token = request.cookies.get(SESSION_COOKIE)
        context = _account_context(request)
        if not context.get("authenticated"):
            raise HTTPException(status_code=401, detail="Authenticated session required.")
        if _hosted_context(context) and context.get("role") not in {"owner", "member"}:
            raise HTTPException(status_code=403, detail="Account role is read-only.")
        manager = _HOSTED_SESSION_MANAGER if _hosted_context(context) else _IDENTITY_SESSION_MANAGER
        if not manager.validate_csrf(session_token, request.cookies.get(CSRF_COOKIE), request.headers.get("x-csrf-token")):
            raise HTTPException(status_code=403, detail="CSRF validation failed.")
        client_key = f"account-write:{context.get('tenant_id')}:{getattr(request.client, 'host', 'unknown')}"
        if not _IDENTITY_RATE_LIMITER.allow(
            client_key,
            limit=30,
            window_seconds=60,
        ):
            raise HTTPException(status_code=429, detail="Account write rate limit reached.")
        return context

    @app.post("/api/account/signout")
    def account_signout(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ):
        del body
        context = require_account_mutation(request)
        token = request.cookies.get(SESSION_COOKIE)
        if _hosted_context(context):
            _HOSTED_SESSION_MANAGER.revoke(token)
        else:
            _IDENTITY_SESSION_MANAGER.revoke(token)
        response = _account_response(
            build_api_account_workspace_payload(
                _account_context(request),
                sync_state="local",
            )
        )
        response.delete_cookie(SESSION_COOKIE, path="/")
        response.delete_cookie(CSRF_COOKIE, path="/")
        return response

    @app.get("/api/account/preferences/{preference_key}")
    def account_preference_get(request: Request, preference_key: str):
        context = _account_context(request)
        if not context.get("authenticated"):
            raise HTTPException(status_code=401, detail="Authenticated session required.")
        try:
            preference = _IDENTITY_PREFERENCE_ADAPTER.get(context, preference_key)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not preference:
            raise HTTPException(status_code=404, detail="Preference not found.")
        return _account_response(
            build_api_account_preference_payload(preference, status="restored")
        )

    @app.put("/api/account/preferences/{preference_key}")
    def account_preference_put(
        request: Request,
        preference_key: str,
        body: dict[str, Any] = Body(default={}),
    ):
        context = require_account_mutation(request)
        try:
            validated = validate_preference_body(body)
            preference = _IDENTITY_PREFERENCE_ADAPTER.save(
                context,
                preference_key,
                validated["value"],
                expected_version=validated["expected_version"],
            )
        except PreferenceConflict as exc:
            payload = build_api_account_preference_payload(
                {"current_version": exc.current_version},
                status="conflict",
            )
            return _account_response(payload, status_code=409)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        persistence = _sync_account_continuity(
            context,
            "preference-save",
            {"preference_key": preference_key, "version": preference.get("version")},
        )
        payload = build_api_account_preference_payload(
            preference,
            status="saved",
            persistence=persistence,
        )
        return _account_response(payload)

    @app.delete("/api/account/preferences/{preference_key}")
    def account_preference_delete(
        request: Request,
        preference_key: str,
        expected_version: int,
    ):
        context = require_account_mutation(request)
        try:
            preference = _IDENTITY_PREFERENCE_ADAPTER.get(context, preference_key)
            if not preference:
                raise HTTPException(status_code=404, detail="Preference not found.")
            deleted = _IDENTITY_PREFERENCE_ADAPTER.delete(
                context,
                str(preference.get("resource_id") or ""),
                expected_version=expected_version,
            )
        except PreferenceConflict as exc:
            return _account_response(
                build_api_account_preference_payload(
                    {"current_version": exc.current_version},
                    status="conflict",
                ),
                status_code=409,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        persistence = _sync_account_continuity(
            context,
            "preference-delete",
            {"preference_key": preference_key, "expected_version": expected_version},
        )
        payload = build_api_account_preference_payload(
            {"preference_key": preference_key, "deleted": deleted},
            status="deleted",
            persistence=persistence,
        )
        return _account_response(payload)

    @app.get("/api/account/export")
    def account_export(request: Request):
        context = _account_context(request)
        if not context.get("authenticated"):
            raise HTTPException(status_code=401, detail="Authenticated session required.")
        export = _IDENTITY_PREFERENCE_ADAPTER.export(context)
        return _account_response(
            {
                "contract_version": "phase_2b.v1",
                "payload_type": "account_export",
                "generated_at": export.get("exported_at"),
                "data": export,
                "summary": {"preference_count": len(export.get("preferences") or [])},
                "source_status": [],
                "unavailable": [],
                "errors": [],
                "caveats": ["Export is bounded to the current server-derived tenant."],
            }
        )

    def require_account_read(request: Request) -> dict[str, Any]:
        context = _account_context(request)
        if not context.get("authenticated"):
            raise HTTPException(status_code=401, detail="Authenticated session required.")
        return context

    def tenant_research_response(
        data: dict[str, Any],
        *,
        payload_type: str,
        status: str = "ready",
        status_code: int = 200,
        context: dict[str, Any] | None = None,
        continuity_operation: str | None = None,
        continuity_evidence: Any = None,
    ):
        if context is not None and continuity_operation:
            data = _with_account_continuity(
                data,
                context,
                continuity_operation,
                continuity_evidence,
            )
        return _account_response(
            build_api_tenant_research_desk_payload(
                data,
                payload_type=payload_type,
                status=status,
            ),
            status_code=status_code,
        )

    @app.get("/api/account/research-desk")
    def account_research_desk(request: Request):
        context = require_account_read(request)
        contract = _TENANT_RESEARCH_REPOSITORY.build_contract(context)
        contract["sync"] = _TENANT_RESEARCH_SYNC.status(context)
        return tenant_research_response(
            contract,
            payload_type="tenant_research_desk",
        )

    @app.get("/api/account/attention-desk")
    def account_attention_desk(request: Request, mode: str = "cache"):
        context = require_account_read(request)
        try:
            return _account_response(get_attention_desk_payload(mode=mode, context=context))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/account/observation-runs")
    def account_observation_runs(request: Request, watchlist_id: str | None = None, limit: int = 20):
        context = require_account_read(request)
        try:
            runs = _OBSERVATION_RUN_STORE.list_runs(
                context,
                watchlist_id=str(watchlist_id or "") or None,
                limit=limit,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _account_response(
            build_api_observation_run_payload(
                {
                    "runs": runs,
                    "attention": _OBSERVATION_RUN_STORE.build_attention_context(context),
                    "provider_call_count": 0,
                },
                payload_type="observation_runs",
                status="ready",
            )
        )

    @app.post("/api/account/observation-runs")
    def account_observation_run_start(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ):
        context = require_account_mutation(request)
        try:
            run = _OBSERVATION_RUN_COORDINATOR.submit(context, body)
        except ObservationRunBusy as exc:
            return _account_response(
                build_api_observation_run_payload(
                    {"status": "busy", "active_run_id": exc.active_run_id, "provider_call_count": 0},
                    status="busy",
                ),
                status_code=409,
            )
        except ObservationRunConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        status_code = 202 if run.get("status") in {"queued", "running"} else 201
        run = _with_account_continuity(
            run,
            context,
            "observation-submit",
            {"run_id": run.get("run_id"), "status": run.get("status"), "version": run.get("version")},
        )
        return _account_response(
            build_api_observation_run_payload(run, status=str(run.get("status") or "queued")),
            status_code=status_code,
        )

    @app.get("/api/account/observation-runs/{run_id}")
    def account_observation_run_get(request: Request, run_id: str):
        context = require_account_read(request)
        run = _OBSERVATION_RUN_STORE.get_run(context, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Observation run not found.")
        return _account_response(
            build_api_observation_run_payload(run, status=str(run.get("status") or "ready"))
        )

    @app.get("/api/account/observation-runs/{run_id}/snapshots")
    def account_observation_run_snapshots(request: Request, run_id: str):
        context = require_account_read(request)
        run = _OBSERVATION_RUN_STORE.get_run(context, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Observation run not found.")
        snapshots = _OBSERVATION_RUN_STORE.list_snapshots(context, run_id)
        return _account_response(
            build_api_observation_run_payload(
                {"run_id": run_id, "snapshots": snapshots, "provider_call_count": 0},
                payload_type="observation_snapshots",
                status="ready",
            )
        )

    @app.post("/api/account/observation-runs/{run_id}/cancel")
    def account_observation_run_cancel(
        request: Request,
        run_id: str,
        body: dict[str, Any] = Body(default={}),
    ):
        del body
        context = require_account_mutation(request)
        try:
            run = _OBSERVATION_RUN_COORDINATOR.cancel(context, run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        run = _with_account_continuity(
            run,
            context,
            "observation-cancel",
            {"run_id": run_id, "status": run.get("status"), "version": run.get("version")},
        )
        return _account_response(
            build_api_observation_run_payload(run, status=str(run.get("status") or "cancelled"))
        )

    def alert_manager_response(
        data: dict[str, Any],
        *,
        payload_type: str = "watchlist_alert_manager",
        status: str | None = None,
        status_code: int = 200,
        context: dict[str, Any] | None = None,
        continuity_operation: str | None = None,
        continuity_evidence: Any = None,
    ):
        if context is not None and continuity_operation:
            data = _with_account_continuity(
                data,
                context,
                continuity_operation,
                continuity_evidence,
            )
        return _account_response(
            build_api_watchlist_alert_manager_payload(
                data,
                payload_type=payload_type,
                status=status,
            ),
            status_code=status_code,
        )

    @app.get("/api/account/alert-manager")
    def account_alert_manager(request: Request):
        context = require_account_read(request)
        contract = build_watchlist_alert_manager_contract(context, store=_ALERT_MANAGER_STORE)
        return alert_manager_response(contract)

    def hosted_scheduler_response(
        data: dict[str, Any],
        *,
        payload_type: str = "hosted_scheduler_operations",
        status: str | None = None,
        status_code: int = 200,
        context: dict[str, Any] | None = None,
        continuity_operation: str | None = None,
        continuity_evidence: Any = None,
        materialize_schedule: dict[str, Any] | None = None,
        materialize_expected_version: int = 0,
    ):
        if context is not None and continuity_operation:
            data = _with_account_continuity(
                data,
                context,
                continuity_operation,
                continuity_evidence,
            )
        if context is not None and materialize_schedule is not None and _hosted_context(context):
            try:
                data["hosted_materialization"] = _HOSTED_SCHEDULER_REPOSITORY.apply(
                    context,
                    materialize_schedule,
                    expected_version=materialize_expected_version,
                )
            except SupabaseRepositoryConflict as exc:
                data["hosted_materialization"] = {
                    "status": "conflict",
                    "current_version": exc.current_version,
                    "provider_call_count": 0,
                    "caveat": "The local account document was retained; reload before retrying hosted schedule materialization.",
                }
            except (SupabaseAuthenticationError, SupabaseRepositoryUnavailable):
                data["hosted_materialization"] = {
                    "status": "unavailable",
                    "provider_call_count": 0,
                    "caveat": "Hosted schedule materialization was not confirmed; the recurring runner will not claim this local-only change.",
                }
        return _account_response(
            build_api_hosted_scheduler_operations_payload(
                data,
                payload_type=payload_type,
                status=status,
            ),
            status_code=status_code,
        )

    @app.get("/api/account/alert-manager/scheduler")
    def account_hosted_scheduler(request: Request):
        context = require_account_read(request)
        contract = _HOSTED_SCHEDULER_STORE.build_contract(context)
        if _hosted_context(context):
            try:
                contract = merge_hosted_scheduler_repository_rows(
                    contract,
                    _HOSTED_SCHEDULER_REPOSITORY.read_contract_rows(context),
                )
            except (SupabaseAuthenticationError, SupabaseRepositoryUnavailable):
                contract["hosted_repository"] = {
                    "contacted": True,
                    "source_status": "unavailable",
                    "provider_call_count": 0,
                    "configured_is_not_verified": True,
                }
        return hosted_scheduler_response(contract)

    @app.post("/api/account/alert-manager/scheduler/schedules")
    def account_hosted_scheduler_create(request: Request, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            schedule = _HOSTED_SCHEDULER_STORE.create_schedule(context, body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        data = _HOSTED_SCHEDULER_STORE.build_contract(context)
        data["schedule"] = schedule
        return hosted_scheduler_response(
            data,
            payload_type="hosted_scheduler_schedule",
            status="created-disabled",
            status_code=201,
            context=context,
            continuity_operation="hosted-schedule-create",
            continuity_evidence={"schedule_id": schedule.get("schedule_id"), "state": schedule.get("state"), "version": schedule.get("version")},
            materialize_schedule=schedule,
            materialize_expected_version=0,
        )

    @app.patch("/api/account/alert-manager/scheduler/schedules/{schedule_id}")
    def account_hosted_scheduler_update(
        request: Request,
        schedule_id: str,
        body: dict[str, Any] = Body(default={}),
    ):
        context = require_account_mutation(request)
        try:
            schedule = _HOSTED_SCHEDULER_STORE.update_schedule(context, schedule_id, body)
        except HostedSchedulerConflict as exc:
            return hosted_scheduler_response(
                {
                    "contract_version": "hosted_scheduler_operations.v1",
                    "current_version": exc.current_version,
                    "summary": {"status": "conflict", "provider_call_count": 0},
                },
                payload_type="hosted_scheduler_schedule",
                status="conflict",
                status_code=409,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        data = _HOSTED_SCHEDULER_STORE.build_contract(context)
        data["schedule"] = schedule
        action = str(body.get("action") or "updated")
        return hosted_scheduler_response(
            data,
            payload_type="hosted_scheduler_schedule",
            status=str(schedule.get("state") or "updated"),
            context=context,
            continuity_operation=f"hosted-schedule-{action}",
            continuity_evidence={"schedule_id": schedule_id, "state": schedule.get("state"), "version": schedule.get("version")},
            materialize_schedule=schedule,
            materialize_expected_version=max(0, int(body.get("expected_version") or 0)),
        )

    @app.get("/api/account/alert-manager/scheduler/audit")
    def account_hosted_scheduler_audit(request: Request, limit: int = 100):
        context = require_account_read(request)
        rows = _HOSTED_SCHEDULER_STORE.list_audit(context, limit=limit)
        return hosted_scheduler_response(
            {
                "contract_version": "hosted_scheduler_operations.v1",
                "audit": rows,
                "summary": {"status": "ready", "row_count": len(rows), "provider_call_count": 0},
            },
            payload_type="hosted_scheduler_audit",
        )

    @app.post("/api/account/alert-manager/rules")
    def account_alert_rule_create(request: Request, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            rule = _ALERT_MANAGER_STORE.create_rule(context, body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return alert_manager_response(
            {"contract_version": "watchlist_alert_manager.v1", "rule": rule, "summary": {"status": "created", "provider_call_count": 0}},
            payload_type="watchlist_alert_rule",
            status="created",
            status_code=201,
            context=context,
            continuity_operation="alert-rule-create",
            continuity_evidence={"resource_id": rule.get("resource_id"), "version": rule.get("version")},
        )

    @app.get("/api/account/alert-manager/rules/{resource_id}")
    def account_alert_rule_get(request: Request, resource_id: str):
        context = require_account_read(request)
        rule = _ALERT_MANAGER_STORE.get_rule(context, resource_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found.")
        return alert_manager_response(
            {"contract_version": "watchlist_alert_manager.v1", "rule": rule, "summary": {"status": "ready", "provider_call_count": 0}},
            payload_type="watchlist_alert_rule",
        )

    @app.patch("/api/account/alert-manager/rules/{resource_id}")
    def account_alert_rule_update(request: Request, resource_id: str, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            rule = _ALERT_MANAGER_STORE.update_rule(context, resource_id, body)
        except AlertManagerConflict as exc:
            return alert_manager_response(
                {"contract_version": "watchlist_alert_manager.v1", "current_version": exc.current_version, "summary": {"status": "conflict", "provider_call_count": 0}},
                payload_type="watchlist_alert_rule",
                status="conflict",
                status_code=409,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return alert_manager_response(
            {"contract_version": "watchlist_alert_manager.v1", "rule": rule, "summary": {"status": str(rule.get("state") or "updated"), "provider_call_count": 0}},
            payload_type="watchlist_alert_rule",
            context=context,
            continuity_operation="alert-rule-update",
            continuity_evidence={"resource_id": resource_id, "version": rule.get("version")},
        )

    @app.delete("/api/account/alert-manager/rules/{resource_id}")
    def account_alert_rule_delete(request: Request, resource_id: str, expected_version: int):
        context = require_account_mutation(request)
        try:
            deleted = _ALERT_MANAGER_STORE.delete_rule(context, resource_id, expected_version=expected_version)
        except AlertManagerConflict as exc:
            return alert_manager_response(
                {"contract_version": "watchlist_alert_manager.v1", "current_version": exc.current_version, "summary": {"status": "conflict", "provider_call_count": 0}},
                payload_type="watchlist_alert_rule",
                status="conflict",
                status_code=409,
            )
        if not deleted:
            raise HTTPException(status_code=404, detail="Alert rule not found.")
        return alert_manager_response(
            {"contract_version": "watchlist_alert_manager.v1", "resource_id": resource_id, "deleted": True, "summary": {"status": "deleted", "provider_call_count": 0}},
            payload_type="watchlist_alert_rule",
            status="deleted",
            context=context,
            continuity_operation="alert-rule-delete",
            continuity_evidence={"resource_id": resource_id, "expected_version": expected_version},
        )

    @app.post("/api/account/alert-manager/evaluations")
    def account_alert_evaluation(request: Request, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            evaluation = _ALERT_MANAGER_STORE.evaluate_due(context, body)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return alert_manager_response(
            {"contract_version": "watchlist_alert_manager.v1", "evaluation": evaluation, "summary": {"status": evaluation.get("status"), "provider_call_count": 0}},
            payload_type="watchlist_alert_evaluation",
            status=str(evaluation.get("status") or "completed"),
            status_code=201,
            context=context,
            continuity_operation="alert-evaluate",
            continuity_evidence={"run_id": evaluation.get("run_id"), "status": evaluation.get("status")},
        )

    @app.get("/api/account/alert-manager/triggers/{trigger_id}")
    def account_alert_trigger_get(request: Request, trigger_id: str):
        context = require_account_read(request)
        trigger = _ALERT_MANAGER_STORE.get_trigger(context, trigger_id)
        if not trigger:
            raise HTTPException(status_code=404, detail="Alert trigger not found.")
        return alert_manager_response(
            {"contract_version": "watchlist_alert_manager.v1", "trigger": trigger, "summary": {"status": "ready", "provider_call_count": 0}},
            payload_type="watchlist_alert_trigger",
        )

    @app.patch("/api/account/alert-manager/triggers/{trigger_id}")
    def account_alert_trigger_review(request: Request, trigger_id: str, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            trigger = _ALERT_MANAGER_STORE.review_trigger(context, trigger_id, body)
        except AlertManagerConflict as exc:
            return alert_manager_response(
                {"contract_version": "watchlist_alert_manager.v1", "current_version": exc.current_version, "summary": {"status": "conflict", "provider_call_count": 0}},
                payload_type="watchlist_alert_trigger",
                status="conflict",
                status_code=409,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return alert_manager_response(
            {"contract_version": "watchlist_alert_manager.v1", "trigger": trigger, "summary": {"status": trigger.get("review_state"), "provider_call_count": 0}},
            payload_type="watchlist_alert_trigger",
            context=context,
            continuity_operation="alert-trigger-review",
            continuity_evidence={"trigger_id": trigger_id, "version": trigger.get("version")},
        )

    @app.get("/api/account/alert-manager/audit")
    def account_alert_audit(request: Request, limit: int = 100):
        context = require_account_read(request)
        rows = _ALERT_MANAGER_STORE.list_audit(context, limit=limit)
        return alert_manager_response(
            {"contract_version": "watchlist_alert_manager.v1", "audit": rows, "summary": {"status": "ready", "row_count": len(rows), "provider_call_count": 0}},
            payload_type="watchlist_alert_audit",
        )

    @app.get("/api/account/alert-manager/export")
    def account_alert_export(request: Request):
        context = require_account_read(request)
        return alert_manager_response(
            _ALERT_MANAGER_STORE.export_manager(context),
            payload_type="watchlist_alert_export",
        )

    @app.post("/api/account/alert-manager/worker/run-once")
    def account_alert_worker_run_once(request: Request, body: dict[str, Any] = Body(default={})):
        del body
        context = require_account_mutation(request)
        result = run_alert_worker_once(context, store=_ALERT_MANAGER_STORE)
        data = {"contract_version": "watchlist_alert_manager.v1", "worker_run": result, "summary": {"status": result.get("status"), "provider_call_count": int(result.get("provider_call_count") or 0)}}
        return alert_manager_response(
            data,
            payload_type="watchlist_alert_worker",
            status=str(result.get("status") or "disabled"),
            status_code=202 if result.get("status") not in {"disabled"} else 409,
            context=context if result.get("status") not in {"disabled"} else None,
            continuity_operation="alert-worker-run" if result.get("status") not in {"disabled"} else None,
            continuity_evidence={"status": result.get("status"), "run_id": result.get("run_id")},
        )

    @app.patch("/api/account/attention-desk/items/{fingerprint}")
    def account_attention_item_update(
        request: Request,
        fingerprint: str,
        body: dict[str, Any] = Body(default={}),
    ):
        context = require_account_mutation(request)
        try:
            state = _ATTENTION_REVIEW_STORE.update_state(
                context,
                fingerprint,
                action=str(body.get("action") or ""),
                expected_version=int(body.get("expected_version") or 0),
                snoozed_until=body.get("snoozed_until"),
            )
        except AttentionConflict as exc:
            return _account_response(
                build_api_attention_action_payload(
                    {"current_version": exc.current_version},
                    payload_type="attention_review_state",
                    status="conflict",
                ),
                status_code=409,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        state = _with_account_continuity(
            state,
            context,
            "attention-review",
            {"fingerprint": fingerprint, "version": state.get("version"), "state": state.get("review_state")},
        )
        return _account_response(
            build_api_attention_action_payload(
                state,
                payload_type="attention_review_state",
                status=str(state.get("review_state") or "saved"),
            )
        )

    @app.put("/api/account/attention-desk/policy")
    def account_attention_policy(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ):
        context = require_account_mutation(request)
        try:
            expected_version = int(body.get("expected_version") or 0)
            policy = _ATTENTION_REVIEW_STORE.save_policy(
                context,
                body,
                expected_version=expected_version,
            )
        except AttentionConflict as exc:
            return _account_response(
                build_api_attention_action_payload(
                    {"current_version": exc.current_version},
                    payload_type="attention_policy",
                    status="conflict",
                ),
                status_code=409,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        policy = _with_account_continuity(
            policy,
            context,
            "attention-policy",
            {"version": policy.get("version")},
        )
        return _account_response(
            build_api_attention_action_payload(policy, payload_type="attention_policy", status="saved")
        )

    @app.post("/api/account/attention-desk/checkpoint")
    def account_attention_checkpoint(
        request: Request,
        body: dict[str, Any] = Body(default={}),
    ):
        context = require_account_mutation(request)
        if any(field in body for field in ("tenant_id", "user_id", "owner_user_id")):
            raise HTTPException(status_code=422, detail="Tenant and user identity are server-derived.")
        try:
            checkpoint = _ATTENTION_REVIEW_STORE.mark_checkpoint(
                context,
                expected_version=int(body.get("expected_version") or 0),
            )
        except AttentionConflict as exc:
            return _account_response(
                build_api_attention_action_payload(
                    {"current_version": exc.current_version},
                    payload_type="attention_checkpoint",
                    status="conflict",
                ),
                status_code=409,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        checkpoint = _with_account_continuity(
            checkpoint,
            context,
            "attention-checkpoint",
            {"version": checkpoint.get("version")},
        )
        return _account_response(
            build_api_attention_action_payload(checkpoint, payload_type="attention_checkpoint", status="saved")
        )

    @app.get("/api/account/attention-desk/audit")
    def account_attention_audit(request: Request, limit: int = 50):
        context = require_account_read(request)
        return _account_response(
            build_api_attention_action_payload(
                _ATTENTION_REVIEW_STORE.list_audit(context, limit=limit),
                payload_type="attention_audit",
            )
        )

    @app.get("/api/account/research-desk/sync")
    def account_research_sync_status(request: Request):
        context = require_account_read(request)
        return tenant_research_response(
            _TENANT_RESEARCH_SYNC.status(context),
            payload_type="tenant_research_sync_status",
        )

    @app.get("/api/account/continuity")
    def account_continuity_status(request: Request):
        context = require_account_read(request)
        return tenant_research_response(
            _ACCOUNT_CONTINUITY.status(context),
            payload_type="account_continuity_status",
        )

    @app.post("/api/account/continuity/replay")
    def account_continuity_replay(request: Request, body: dict[str, Any] = Body(default={})):
        del body
        context = require_account_mutation(request)
        result = _ACCOUNT_CONTINUITY.replay(context)
        return tenant_research_response(
            result,
            payload_type="account_continuity_replay",
            status=str(result.get("status") or "ready"),
        )

    @app.post("/api/account/continuity/resolve")
    def account_continuity_resolve(request: Request, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        if any(key in body for key in ("tenant_id", "user_id", "owner_user_id")):
            raise HTTPException(status_code=422, detail="Account identity is server-derived.")
        try:
            result = _ACCOUNT_CONTINUITY.resolve_conflict(
                context,
                strategy=str(body.get("strategy") or ""),
                idempotency_key=str(body.get("idempotency_key") or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        status_code = 409 if result.get("status") == "conflict" else 200
        return tenant_research_response(
            result,
            payload_type="account_continuity_resolution",
            status=str(result.get("status") or "ready"),
            status_code=status_code,
        )

    @app.get("/api/account/continuity/export")
    def account_continuity_export(request: Request):
        context = require_account_read(request)
        return tenant_research_response(
            _ACCOUNT_CONTINUITY.export(context),
            payload_type="account_continuity_export",
        )

    @app.post("/api/account/continuity/import")
    def account_continuity_import(request: Request, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        if any(key in body for key in ("tenant_id", "user_id", "owner_user_id")):
            raise HTTPException(status_code=422, detail="Account identity is server-derived.")
        bundle = body.get("bundle")
        if not isinstance(bundle, dict):
            raise HTTPException(status_code=422, detail="A bounded account backup is required.")
        try:
            result = _ACCOUNT_CONTINUITY.import_backup(
                context,
                bundle,
                strategy=str(body.get("strategy") or "merge"),
                idempotency_key=str(body.get("idempotency_key") or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return tenant_research_response(
            result,
            payload_type="account_continuity_import",
            status=str(result.get("status") or "restored"),
            status_code=409 if result.get("status") == "conflict" else 200,
        )

    @app.delete("/api/account/continuity")
    def account_continuity_delete(request: Request, idempotency_key: str):
        context = require_account_mutation(request)
        try:
            result = _ACCOUNT_CONTINUITY.delete_hosted(
                context,
                idempotency_key=str(idempotency_key or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        status_code = 409 if result.get("status") == "conflict" else 200
        return tenant_research_response(
            result,
            payload_type="account_continuity_delete",
            status=str(result.get("status") or "ready"),
            status_code=status_code,
        )

    @app.get("/api/account/research-desk/sync/preview")
    def account_research_sync_preview(request: Request):
        context = require_account_read(request)
        return tenant_research_response(
            _TENANT_RESEARCH_SYNC.preview(context),
            payload_type="tenant_research_sync_preview",
        )

    @app.post("/api/account/research-desk/sync/queue")
    def account_research_sync_queue(request: Request, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            queued = _TENANT_RESEARCH_SYNC.queue_first_sync(context, body)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return tenant_research_response(
            queued,
            payload_type="tenant_research_sync_mutation",
            status=str(queued.get("status") or "pending"),
            status_code=201,
        )

    @app.post("/api/account/research-desk/sync/replay")
    def account_research_sync_replay(request: Request, body: dict[str, Any] = Body(default={})):
        del body
        context = require_account_mutation(request)
        replay = _TENANT_RESEARCH_SYNC.replay(context)
        return tenant_research_response(
            replay,
            payload_type="tenant_research_sync_replay",
            status=str(replay.get("status") or "ready"),
        )

    @app.delete("/api/account/research-desk/sync/queue/{mutation_id}")
    def account_research_sync_cancel(request: Request, mutation_id: str):
        context = require_account_mutation(request)
        if not _TENANT_RESEARCH_SYNC.cancel(context, mutation_id):
            raise HTTPException(status_code=404, detail="Sync mutation not found.")
        return tenant_research_response(
            {"mutation_id": mutation_id, "status": "canceled", "provider_call_count": 0},
            payload_type="tenant_research_sync_mutation",
            status="canceled",
        )

    @app.get("/api/account/research-desk/imports/preview")
    def account_research_import_preview(request: Request, source_list_id: str = "primary", limit: int = 25):
        context = require_account_read(request)
        try:
            preview = _TENANT_RESEARCH_REPOSITORY.preview_import(
                context,
                source_list_id=source_list_id,
                limit=limit,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return tenant_research_response(preview, payload_type="tenant_research_import_preview")

    @app.post("/api/account/research-desk/imports")
    def account_research_import(request: Request, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            imported = _TENANT_RESEARCH_REPOSITORY.confirm_import(context, body)
        except TenantResearchConflict as exc:
            return tenant_research_response(
                {"current_version": exc.current_version},
                payload_type="tenant_research_import",
                status="conflict",
                status_code=409,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return tenant_research_response(
            imported,
            payload_type="tenant_research_import",
            status=str(imported.get("status") or "imported"),
            status_code=201,
            context=context,
            continuity_operation="watchlist-import",
            continuity_evidence={
                "resource_id": imported.get("resource_id"),
                "version": imported.get("version"),
                "status": imported.get("status"),
            },
        )

    @app.get("/api/account/research-desk/watchlists/{resource_id}")
    def account_research_watchlist(request: Request, resource_id: str):
        context = require_account_read(request)
        watchlist = _TENANT_RESEARCH_REPOSITORY.get_watchlist(context, resource_id)
        if not watchlist:
            raise HTTPException(status_code=404, detail="Account watchlist not found.")
        return tenant_research_response(watchlist, payload_type="tenant_research_watchlist")

    @app.delete("/api/account/research-desk/watchlists/{resource_id}")
    def account_research_watchlist_delete(request: Request, resource_id: str, expected_version: int):
        context = require_account_mutation(request)
        try:
            deleted = _TENANT_RESEARCH_REPOSITORY.delete_watchlist(
                context,
                resource_id,
                expected_version=expected_version,
            )
        except TenantResearchConflict as exc:
            return tenant_research_response(
                {"current_version": exc.current_version},
                payload_type="tenant_research_watchlist",
                status="conflict",
                status_code=409,
            )
        if not deleted:
            raise HTTPException(status_code=404, detail="Account watchlist not found.")
        return tenant_research_response(
            {"resource_id": resource_id, "deleted": True},
            payload_type="tenant_research_watchlist",
            status="deleted",
            context=context,
            continuity_operation="watchlist-delete",
            continuity_evidence={"resource_id": resource_id, "expected_version": expected_version},
        )

    @app.put("/api/account/research-desk/watchlists/{resource_id}/rule")
    def account_research_rule(request: Request, resource_id: str, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            rule = _TENANT_RESEARCH_REPOSITORY.configure_rule(
                context,
                resource_id,
                enabled=bool(body.get("enabled")),
                minimum_severity=str(body.get("minimum_severity") or "material"),
                cooldown_minutes=int(body.get("cooldown_minutes") or 0),
                expected_version=int(body.get("expected_version") or 0),
                expires_at=body.get("expires_at"),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Account watchlist not found.") from exc
        except TenantResearchConflict as exc:
            return tenant_research_response(
                {"current_version": exc.current_version},
                payload_type="tenant_research_rule",
                status="conflict",
                status_code=409,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return tenant_research_response(
            rule,
            payload_type="tenant_research_rule",
            status="saved",
            context=context,
            continuity_operation="watchlist-rule",
            continuity_evidence={"resource_id": resource_id, "version": rule.get("version")},
        )

    @app.post("/api/account/research-desk/watchlists/{resource_id}/inbox")
    def account_research_scan(request: Request, resource_id: str, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            scan = _TENANT_RESEARCH_REPOSITORY.scan_inbox(
                context,
                resource_id,
                kill_switch=bool(body.get("kill_switch")),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Account watchlist not found.") from exc
        return tenant_research_response(
            scan,
            payload_type="tenant_research_scan",
            status=str(scan.get("status") or "ready"),
            context=context,
            continuity_operation="watchlist-scan",
            continuity_evidence={
                "resource_id": resource_id,
                "status": scan.get("status"),
                "created_count": scan.get("created_count"),
            },
        )

    @app.get("/api/account/research-desk/inbox/{resource_id}")
    def account_research_inbox_item(request: Request, resource_id: str):
        context = require_account_read(request)
        item = _TENANT_RESEARCH_REPOSITORY.get_inbox_item(context, resource_id)
        if not item:
            raise HTTPException(status_code=404, detail="Account inbox item not found.")
        return tenant_research_response(item, payload_type="tenant_research_inbox_item")

    @app.patch("/api/account/research-desk/inbox/{resource_id}")
    def account_research_inbox_update(request: Request, resource_id: str, body: dict[str, Any] = Body(default={})):
        context = require_account_mutation(request)
        try:
            item = _TENANT_RESEARCH_REPOSITORY.update_inbox_state(
                context,
                resource_id,
                state=str(body.get("state") or ""),
                expected_version=int(body.get("expected_version") or 0),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Account inbox item not found.") from exc
        except TenantResearchConflict as exc:
            return tenant_research_response(
                {"current_version": exc.current_version},
                payload_type="tenant_research_inbox_item",
                status="conflict",
                status_code=409,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return tenant_research_response(
            item,
            payload_type="tenant_research_inbox_item",
            status="saved",
            context=context,
            continuity_operation="inbox-review",
            continuity_evidence={"resource_id": resource_id, "version": item.get("version"), "state": item.get("state")},
        )

    @app.get("/api/account/research-desk/export")
    def account_research_export(request: Request):
        context = require_account_read(request)
        return tenant_research_response(
            _TENANT_RESEARCH_REPOSITORY.export(context),
            payload_type="tenant_research_export",
        )

    @app.get("/api/symbol-intelligence")
    def symbol_intelligence(
        request: Request,
        symbol: str = "AAPL",
        asset_class: str | None = None,
        interval: str = "1d",
        range: str = "3mo",
        runtime_mode: str = "fixture",
        chart_type: str = "candlestick",
        panels: str | None = None,
        compare: str | None = None,
    ):
        payload = get_symbol_workstation_payload(
            symbol=symbol,
            asset_class=asset_class,
            interval=interval,
            range_name=range,
            runtime_mode=runtime_mode,
            chart_type=chart_type,
            panels=panels,
            compare=compare,
        )
        return _symbol_payload_response(request, payload)

    @app.get("/api/provider-health")
    def provider_health() -> dict[str, Any]:
        return get_provider_health_payload()

    @app.get("/api/layers")
    def layers(include_runtime: bool = False) -> dict[str, Any]:
        return get_layers_payload(include_runtime=include_runtime)

    @app.get("/api/news")
    def news(include_runtime: bool = False, query: str = "geopolitical risk OR oil OR macro OR crypto") -> dict[str, Any]:
        return get_news_payload(include_runtime=include_runtime, query=query)

    @app.get("/api/war-room")
    def war_room(include_runtime: bool = False) -> dict[str, Any]:
        return get_war_room_payload(include_runtime=include_runtime)

    @app.get("/api/ai-providers")
    def ai_providers(preferred: str = "auto") -> dict[str, Any]:
        return get_ai_providers_payload(preferred=preferred)

    @app.get("/api/asset-universe")
    def asset_universe() -> dict[str, Any]:
        return get_asset_universe_payload()

    @app.get("/api/event-asset-graph")
    def event_asset_graph(include_runtime: bool = False) -> dict[str, Any]:
        return get_event_asset_graph_payload(include_runtime=include_runtime)

    @app.get("/api/command-workspace")
    def command_workspace(include_runtime: bool = False) -> dict[str, Any]:
        return get_command_workspace_payload(include_runtime=include_runtime)

    @app.get("/api/war-room-map")
    def war_room_map(include_runtime: bool = False) -> dict[str, Any]:
        return get_war_room_map_payload(include_runtime=include_runtime)

    @app.get("/api/map-news-event-fusion")
    def map_news_event_fusion(include_runtime: bool = False) -> dict[str, Any]:
        return get_map_news_event_fusion_payload(include_runtime=include_runtime)

    @app.get("/api/war-room-map-snapshots")
    def war_room_map_snapshots() -> dict[str, Any]:
        return get_war_room_map_replay_payload()

    @app.post("/api/war-room-map-snapshots")
    def war_room_map_snapshot_capture(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        try:
            return capture_war_room_map_replay_payload(
                runtime_mode=str(payload.get("runtime_mode") or "cache"),
                retention_days=int(payload.get("retention_days") or 30),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/war-room-map-replay")
    def war_room_map_replay(time: str | None = None, compareTo: str | None = None) -> dict[str, Any]:
        try:
            return get_war_room_map_replay_payload(snapshot_id=time, compare_to=compareTo)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/research-report")
    def research_report(
        include_runtime: bool = False,
        symbol: str = "AAPL",
        crypto_symbol: str = "BTCUSDT",
    ) -> dict[str, Any]:
        return get_research_report_payload(
            include_runtime=include_runtime,
            symbol=symbol,
            crypto_symbol=crypto_symbol,
        )

    @app.get("/api/research-memory")
    def research_memory(
        mode: str = "demo",
        collection: str = "demo-research",
        surface: str = "inbox",
        memory_type: str = "",
        tag: str = "",
    ) -> dict[str, Any]:
        return get_research_memory_payload(
            mode=mode,
            collection_id=collection,
            surface=surface,
            memory_type=memory_type,
            tag=tag,
        )

    @app.get("/api/daily-brief")
    def daily_brief(mode: str = "cache", period: str = "morning") -> dict[str, Any]:
        try:
            return get_daily_brief_payload(mode=mode, period=period)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/daily-brief/captures")
    def daily_brief_captures(period: str | None = None) -> dict[str, Any]:
        from lib.daily_briefing import list_daily_brief_captures

        try:
            rows = list_daily_brief_captures(period=period)
            return {"ok": True, "privacy_scope": "local-private", "captures": rows}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/daily-brief/captures")
    def daily_brief_capture(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        try:
            return capture_daily_brief_payload(
                mode=str(payload.get("mode") or "cache"),
                period=str(payload.get("period") or "morning"),
                retention_days=int(payload.get("retention_days") or 90),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.patch("/api/daily-brief/captures/{brief_id}/review")
    def daily_brief_review(brief_id: str, payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.daily_briefing import update_daily_brief_review

        try:
            capture = update_daily_brief_review(
                brief_id,
                status=str(payload.get("status") or "reviewed"),
                review_notes=str(payload.get("review_notes") or ""),
            )
            return {"ok": True, "privacy_scope": "local-private", "capture": capture}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/research-memory/search")
    def research_memory_search(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.research_memory import search_memory_items

        rows = search_memory_items(
            str(payload.get("query") or ""),
            collection_id=str(payload.get("collection_id") or "local-research"),
            limit=int(payload.get("limit") or 50),
            include_private=bool(payload.get("include_private", False)),
        )
        return {"ok": True, "privacy_scope": "local-private", "items": rows, "query_transport": "POST-body"}

    @app.post("/api/research-memory/items")
    def research_memory_create(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.research_memory import save_memory_item

        try:
            item = save_memory_item(
                collection_id=str(payload.get("collection_id") or "local-research"),
                memory_type=str(payload.get("memory_type") or "note"),
                title=str(payload.get("title") or "Local research note"),
                private_body=str(payload.get("private_body") or ""),
                sanitized_summary=str(payload.get("sanitized_summary") or ""),
                origin_id=str(payload.get("origin_id") or ""),
                compatibility_period=str(payload.get("compatibility_period") or ""),
                compatibility_model=str(payload.get("compatibility_model") or ""),
                linked_symbols=payload.get("linked_symbols") or [],
                linked_events=payload.get("linked_events") or [],
                linked_reports=payload.get("linked_reports") or [],
                tags=payload.get("tags") or [],
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "item": item}

    @app.get("/api/research-memory/items/{memory_id}")
    def research_memory_detail(memory_id: str, include_private: bool = False) -> dict[str, Any]:
        from lib.research_memory import get_memory_item

        try:
            item = get_memory_item(memory_id, include_private=include_private)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not item:
            raise HTTPException(status_code=404, detail="Research memory item not found.")
        return {"ok": True, "privacy_scope": "local-private", "item": item}

    @app.delete("/api/research-memory/items/{memory_id}")
    def research_memory_archive(memory_id: str) -> dict[str, Any]:
        from lib.research_memory import archive_memory_item

        return {"ok": archive_memory_item(memory_id), "memory_id": memory_id}

    @app.post("/api/research-memory/source-snapshots")
    def research_memory_source_snapshot(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.research_memory import append_source_snapshot

        try:
            row = append_source_snapshot(
                str(payload.get("memory_id") or ""),
                provider=str(payload.get("provider") or "unknown"),
                source_url=str(payload.get("source_url") or ""),
                fetched_at=payload.get("fetched_at"),
                freshness=str(payload.get("freshness") or "unknown"),
                source_status=str(payload.get("source_status") or "unknown"),
                confidence=float(payload.get("confidence") or 0.0),
                caveat=str(payload.get("caveat") or ""),
                data_gap=str(payload.get("data_gap") or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "snapshot": row}

    @app.post("/api/research-memory/watchlists")
    def research_memory_watchlist_add(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.research_memory import add_local_watchlist_item

        try:
            item = add_local_watchlist_item(
                symbol=str(payload.get("symbol") or ""),
                display_name=str(payload.get("display_name") or ""),
                item_type=str(payload.get("item_type") or "asset"),
                watch_reason=str(payload.get("watch_reason") or "Research monitoring"),
                tags=payload.get("tags") or [],
            )
        except (ValueError, IndexError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "item": item}

    @app.delete("/api/research-memory/watchlists/{item_id}")
    def research_memory_watchlist_remove(item_id: str) -> dict[str, Any]:
        from lib.research_memory import remove_local_watchlist_item

        return {"ok": remove_local_watchlist_item(item_id), "item_id": item_id}

    @app.get("/api/watchlist-desk")
    def watchlist_desk(
        mode: str = "fixture",
        list_id: str = "primary",
        selected: str | None = None,
    ) -> dict[str, Any]:
        try:
            return get_watchlist_desk_payload(mode=mode, list_id=list_id, selected=selected)
        except (KeyError, ValueError) as exc:
            status_code = 404 if isinstance(exc, KeyError) else 422
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    @app.get("/api/watchlist-desk/lists/{list_id}/changes")
    def watchlist_desk_changes(request: Request, list_id: str, mode: str = "local"):
        try:
            payload = get_watchlist_change_payload(mode=mode, list_id=list_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _private_payload_response(
            request,
            payload,
            status_header=str(payload.get("summary", {}).get("comparison_status") or "unavailable"),
        )

    @app.post("/api/watchlist-desk/lists/{list_id}/change-alert-rule")
    def watchlist_desk_change_alert_rule(list_id: str, payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.research_snapshot_diff import upsert_watchlist_change_rule
        from lib.watchlist_desk import build_watchlist_change_contract

        try:
            build_watchlist_change_contract(list_id)
            rule = upsert_watchlist_change_rule(
                list_id,
                enabled=bool(payload.get("enabled")),
                minimum_severity=str(payload.get("minimum_severity") or "material"),
                cooldown_minutes=int(payload.get("cooldown_minutes") or 60),
                expires_at=str(payload.get("expires_at") or "") or None,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "delivery": "preview-only", "rule": rule}

    @app.post("/api/watchlist-desk/lists/{list_id}/change-alert-previews")
    def watchlist_desk_change_alert_previews(list_id: str) -> dict[str, Any]:
        from lib.research_snapshot_diff import persist_change_alert_previews
        from lib.watchlist_desk import build_watchlist_change_contract

        try:
            contract = build_watchlist_change_contract(list_id)
            result = persist_change_alert_previews(list_id, contract["change_inbox"])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "delivery": "preview-only", "preview": result}

    @app.patch("/api/watchlist-desk/change-alert-events/{event_id}/acknowledge")
    def watchlist_desk_acknowledge_change_alert(event_id: str) -> dict[str, Any]:
        from lib.research_snapshot_diff import acknowledge_change_alert_event

        try:
            event = acknowledge_change_alert_event(event_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "event": event}

    @app.post("/api/watchlist-desk/lists")
    def watchlist_desk_create_list(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.watchlist_desk import WatchlistConflict, create_watchlist

        try:
            row = create_watchlist(
                str(payload.get("name") or ""),
                list_id=str(payload.get("list_id") or "") or None,
            )
        except WatchlistConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "watchlist": row}

    @app.patch("/api/watchlist-desk/lists/{list_id}")
    def watchlist_desk_rename_list(list_id: str, payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.watchlist_desk import rename_watchlist

        try:
            row = rename_watchlist(list_id, str(payload.get("name") or ""))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "watchlist": row}

    @app.delete("/api/watchlist-desk/lists/{list_id}")
    def watchlist_desk_archive_list(list_id: str) -> dict[str, Any]:
        from lib.watchlist_desk import archive_watchlist

        try:
            archived = archive_watchlist(list_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not archived:
            raise HTTPException(status_code=404, detail="Watchlist not found.")
        return {"ok": True, "privacy_scope": "local-private", "list_id": list_id}

    @app.post("/api/watchlist-desk/lists/{list_id}/items")
    def watchlist_desk_add_item(list_id: str, payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.watchlist_desk import WatchlistConflict, add_watchlist_symbol

        try:
            item = add_watchlist_symbol(
                list_id,
                str(payload.get("symbol") or ""),
                asset_class=str(payload.get("asset_class") or "") or None,
                private_reason=str(payload.get("private_reason") or ""),
            )
        except WatchlistConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "item": item}

    @app.patch("/api/watchlist-desk/lists/{list_id}/order")
    def watchlist_desk_reorder(list_id: str, payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.watchlist_desk import reorder_watchlist

        try:
            items = reorder_watchlist(list_id, payload.get("item_ids") or [])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "privacy_scope": "local-private", "items": items}

    @app.delete("/api/watchlist-desk/lists/{list_id}/items/{item_id}")
    def watchlist_desk_archive_item(list_id: str, item_id: str) -> dict[str, Any]:
        from lib.watchlist_desk import archive_watchlist_symbol

        try:
            archived = archive_watchlist_symbol(list_id, item_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if not archived:
            raise HTTPException(status_code=404, detail="Watchlist item not found.")
        return {"ok": True, "privacy_scope": "local-private", "item_id": item_id}

    @app.post("/api/watchlist-desk/lists/{list_id}/materialize")
    def watchlist_desk_materialize(list_id: str, payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.watchlist_desk import materialize_watchlist

        try:
            job = materialize_watchlist(
                list_id,
                interval=str(payload.get("interval") or "1d"),
                range_name=str(payload.get("range") or "3mo"),
                max_symbols=int(payload.get("max_symbols") or 8),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        status_code = 409 if job.get("status") == "busy" else 200
        if status_code == 409:
            raise HTTPException(status_code=409, detail="another materialization is active")
        return {"ok": True, "privacy_scope": "local-private", "job": job}

    @app.post("/api/research-memory/export")
    def research_memory_export(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        from lib.research_memory import build_sanitized_export

        return build_sanitized_export(collection_id=str(payload.get("collection_id") or "local-research"))

    return app


app = create_app()
