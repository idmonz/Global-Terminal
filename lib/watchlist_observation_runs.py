from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .config import get_settings
from .equity_provider_breadth import (
    fetch_alpha_vantage_overview,
    fetch_finnhub_company_news,
    fetch_finnhub_earnings_calendar,
)
from .identity_tenancy import _require_authenticated, public_account_payload
from .research_snapshot import build_research_snapshot_rows
from .research_snapshot_diff import build_research_snapshot_diff
from .research_workspace_db import get_connection, json_dumps, json_loads, new_id
from .runtime_cache import load_runtime_cache_record
from .symbol_workstation import history_cache_key, resolve_symbol


OBSERVATION_RUN_VERSION = "watchlist_observation_run.v1"
MAX_OBSERVATION_SYMBOLS = 5
MAX_OBSERVATION_PROVIDER_CALLS = 16
MAX_OBSERVATION_CONCURRENCY = 2
MAX_OBSERVATION_TIMEOUT_SECONDS = 75
MAX_OBSERVATION_PAYLOAD_BYTES = 250_000
MAX_SNAPSHOT_BYTES = 120_000
MAX_RUN_HISTORY = 20
ALPHA_VANTAGE_FREE_DAILY_CALLS = 25
FINNHUB_CONSERVATIVE_WINDOW_CALLS = 30

_ACTIVE_STATUSES = {"queued", "running"}
_TERMINAL_STATUSES = {"partial", "completed", "cancelled", "failed"}
_ALL_STATUSES = _ACTIVE_STATUSES | _TERMINAL_STATUSES
_SESSION_POLICIES = {"market-aware", "cache-only", "force-bounded"}
_IDENTITY_FIELDS = {"tenant_id", "user_id", "owner_user_id", "role", "plan"}
_SAFE_IDEMPOTENCY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
_SAFE_RUN_ID = re.compile(r"^obsrun_[0-9a-f]{20}$")
_SAFE_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9._=-]{0,23}$")
_SAFE_ERROR = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
_SOURCE_STATUSES = {
    "live/fresh", "fresh", "cached", "stale", "partial", "rate-limited",
    "missing-key", "quota-deferred", "provider-error", "forbidden",
    "unavailable", "not_applicable", "cancelled",
}
_FORBIDDEN_PAYLOAD_KEYS = {
    "tenant_id", "user_id", "owner_user_id", "session_token", "csrf_token",
    "api_key", "secret", "private_note", "watch_reason", "holdings",
}


class ObservationRunConflict(RuntimeError):
    pass


class ObservationRunBusy(RuntimeError):
    def __init__(self, active_run_id: str):
        super().__init__("A saved-Watchlist observation run is already active.")
        self.active_run_id = active_run_id


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0)


def _iso(value: datetime | str | None = None) -> str | None:
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        return _utc(value).isoformat()
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            parsed = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        else:
            return None
    return _utc(parsed).isoformat()


def _hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _records(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value or [] if isinstance(row, dict)] if isinstance(value, (list, tuple)) else []


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return ""
    return raw[:1_000]


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in _FORBIDDEN_PAYLOAD_KEYS or normalized.endswith(("_secret", "_token", "_path")):
                return True
            if _contains_forbidden_key(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def validate_observation_request(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError("Observation request must be an object.")
    if _IDENTITY_FIELDS.intersection(body):
        raise ValueError("Tenant and user identity are server-derived.")
    key = str(body.get("idempotency_key") or "").strip()
    if not _SAFE_IDEMPOTENCY.fullmatch(key):
        raise ValueError("idempotency_key must contain 8 to 128 safe characters.")
    max_symbols = body.get("max_symbols", MAX_OBSERVATION_SYMBOLS)
    if isinstance(max_symbols, bool) or not isinstance(max_symbols, int):
        raise ValueError("max_symbols must be an integer.")
    if not 1 <= max_symbols <= MAX_OBSERVATION_SYMBOLS:
        raise ValueError(f"max_symbols exceeds the maximum of {MAX_OBSERVATION_SYMBOLS}.")
    interval = str(body.get("interval") or "1d").strip().lower()
    range_name = str(body.get("range") or body.get("range_name") or "3mo").strip().lower()
    policy = str(body.get("session_policy") or "market-aware").strip().lower()
    if interval not in {"1d"}:
        raise ValueError("Phase 6N supports the bounded 1d observation interval only.")
    if range_name not in {"1mo", "3mo", "6mo", "1y"}:
        raise ValueError("Unsupported observation range.")
    if policy not in _SESSION_POLICIES:
        raise ValueError("session_policy must be market-aware, cache-only, or force-bounded.")
    watchlist_id = str(body.get("watchlist_id") or "").strip()
    if watchlist_id and (len(watchlist_id) > 80 or not re.fullmatch(r"[A-Za-z0-9_-]+", watchlist_id)):
        raise ValueError("Invalid saved Watchlist identifier.")
    return {
        "watchlist_id": watchlist_id,
        "idempotency_key": key,
        "interval": interval,
        "range": range_name,
        "max_symbols": max_symbols,
        "session_policy": policy,
    }


def _session_decision(item: dict[str, Any], policy: str, now: datetime) -> dict[str, Any]:
    symbol = str(item.get("symbol") or "").upper()
    asset_class = str(item.get("asset_class") or "equity").lower()
    if policy == "cache-only":
        return {"symbol": symbol, "asset_class": asset_class, "session_state": "not-contacted", "due_mode": "cache-only", "reason": "explicit-cache-only"}
    if policy == "force-bounded":
        return {"symbol": symbol, "asset_class": asset_class, "session_state": "explicit-override", "due_mode": "provider-refresh", "reason": "explicit-force-bounded"}
    if asset_class in {"crypto", "fx", "forex"}:
        return {"symbol": symbol, "asset_class": asset_class, "session_state": "continuous", "due_mode": "provider-refresh", "reason": "continuous-market-asset-class"}
    eastern = now.astimezone(ZoneInfo("America/New_York"))
    weekday = eastern.weekday() < 5
    minute = eastern.hour * 60 + eastern.minute
    regular_proxy = weekday and 570 <= minute < 960
    state = "regular-session-proxy" if regular_proxy else "closed-weekend" if not weekday else "outside-regular-session"
    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "session_state": state,
        "due_mode": "provider-refresh" if regular_proxy else "cache-only",
        "reason": "weekday-time-proxy" if regular_proxy else "closed-session-cache-first",
    }


def _next_day(now: datetime) -> str:
    tomorrow = (now + timedelta(days=1)).date()
    return datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc).isoformat()


def build_observation_run_plan(
    context: dict[str, Any],
    watchlist: dict[str, Any],
    request: dict[str, Any],
    *,
    quota_usage: dict[str, int] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    tenant_id, _ = _require_authenticated(context)
    validated = validate_observation_request(request)
    current = _utc(now)
    watchlist_id = str(watchlist.get("resource_id") or validated.get("watchlist_id") or "").strip()
    if not watchlist_id:
        raise ValueError("A saved Watchlist is required.")
    items = []
    seen: set[str] = set()
    for item in _records(watchlist.get("items")):
        symbol = str(item.get("symbol") or "").upper()
        if not _SAFE_SYMBOL.fullmatch(symbol) or symbol in seen:
            continue
        seen.add(symbol)
        items.append({**item, "symbol": symbol})
        if len(items) >= validated["max_symbols"]:
            break
    symbol_plan = [_session_decision(item, validated["session_policy"], current) for item in items]
    due = [row for row in symbol_plan if row["due_mode"] == "provider-refresh"]
    due_equities = [row for row in due if row["asset_class"] in {"equity", "etf", "index"}]
    usage = {key: max(0, int(value)) for key, value in (quota_usage or {}).items()}
    settings = get_settings()
    alpha_remaining = max(0, ALPHA_VANTAGE_FREE_DAILY_CALLS - usage.get("alpha_vantage_daily", 0))
    finnhub_remaining = max(0, FINNHUB_CONSERVATIVE_WINDOW_CALLS - usage.get("finnhub_window", 0))
    history_calls = 1 if due else 0
    alpha_calls = min(len(due_equities), alpha_remaining) if settings.alphavantage_api_key else 0
    earnings_calls = min(len(due_equities), finnhub_remaining) if settings.finnhub_api_key else 0
    news_calls = min(len(due_equities), max(0, finnhub_remaining - earnings_calls)) if settings.finnhub_api_key else 0
    planned = {
        "yfinance:multi-history": history_calls,
        "alpha-vantage:overview": alpha_calls,
        "finnhub:earnings-calendar": earnings_calls,
        "finnhub:company-news": news_calls,
    }
    skipped: list[dict[str, Any]] = []
    if due_equities and not settings.alphavantage_api_key:
        skipped.append({"provider": "alpha-vantage", "capability": "overview", "reason": "missing-key"})
    elif due_equities and alpha_remaining == 0:
        skipped.append({"provider": "alpha-vantage", "capability": "overview", "reason": "daily-quota-exhausted"})
    if due_equities and not settings.finnhub_api_key:
        skipped.append({"provider": "finnhub", "capability": "earnings/news", "reason": "missing-key"})
    elif due_equities and finnhub_remaining < len(due_equities) * 2:
        skipped.append({"provider": "finnhub", "capability": "earnings/news", "reason": "window-quota-constrained"})
    if not due:
        skipped.append({"provider": "all", "capability": "network-refresh", "reason": "session-or-policy-cache-only"})
    run_id = f"obsrun_{_hash([tenant_id, watchlist_id, validated['idempotency_key']])[:20]}"
    next_safe = _next_day(current) if alpha_remaining == 0 else (current + timedelta(minutes=1)).isoformat()
    return {
        "observation_run_version": OBSERVATION_RUN_VERSION,
        "run_id": run_id,
        "watchlist_resource_id": watchlist_id,
        "watchlist_name": str(watchlist.get("name") or "Saved Watchlist")[:80],
        "requested_symbols": [row["symbol"] for row in symbol_plan],
        "symbol_plan": symbol_plan,
        "session": {
            "policy": validated["session_policy"],
            "evaluated_at": current.isoformat(),
            "calendar_status": "proxy-unverified",
            "market_open_claimed": False,
            "source": "zoneinfo-weekday-time-proxy",
            "caveat": "Weekday/time logic is not an exchange holiday calendar; cache-only decisions are conservative.",
        },
        "provider_budget": {
            "maximum_calls": MAX_OBSERVATION_PROVIDER_CALLS,
            "planned_calls": min(sum(planned.values()), MAX_OBSERVATION_PROVIDER_CALLS),
            "planned_calls_by_operation": planned,
            "alpha_vantage_daily_limit": ALPHA_VANTAGE_FREE_DAILY_CALLS,
            "alpha_vantage_daily_used": usage.get("alpha_vantage_daily", 0),
            "finnhub_conservative_window_limit": FINNHUB_CONSERVATIVE_WINDOW_CALLS,
            "finnhub_window_used": usage.get("finnhub_window", 0),
            "next_safe_refresh_at": next_safe,
        },
        "skipped_capabilities": skipped,
        "bounds": {
            "maximum_symbols": MAX_OBSERVATION_SYMBOLS,
            "maximum_provider_calls": MAX_OBSERVATION_PROVIDER_CALLS,
            "maximum_concurrency": MAX_OBSERVATION_CONCURRENCY,
            "timeout_seconds": MAX_OBSERVATION_TIMEOUT_SECONDS,
            "maximum_payload_bytes": MAX_OBSERVATION_PAYLOAD_BYTES,
        },
        "retry_policy": {"automatic_retries": 0, "backoff_on_429": True},
        "request": validated,
        "generated_at": current.isoformat(),
        "not_financial_advice": True,
    }


class ObservationRunStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path

    @staticmethod
    def _audit(conn: Any, tenant_id: str, user_id: str, run_id: str, event_type: str, prior: str, new: str, now: str, detail: dict[str, Any] | None = None) -> None:
        conn.execute(
            "INSERT INTO tenant_observation_run_audit (event_id, tenant_id, owner_user_id, run_id, event_type, prior_status, new_status, detail_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id("ora"), tenant_id, user_id, run_id, event_type, prior, new, json_dumps(detail or {}), now),
        )

    def create_run(self, context: dict[str, Any], watchlist: dict[str, Any], request: dict[str, Any], plan: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        validated = validate_observation_request(request)
        current = _utc(now).isoformat()
        run_id = str(plan.get("run_id") or "")
        if not _SAFE_RUN_ID.fullmatch(run_id):
            raise ValueError("Invalid observation run plan identity.")
        watchlist_id = str(plan.get("watchlist_resource_id") or "")
        fingerprint = _hash({
            "watchlist": watchlist_id,
            "request": validated,
            "symbols": list(plan.get("requested_symbols") or []),
        })
        with get_connection(self.db_path) as conn:
            existing = conn.execute(
                "SELECT * FROM tenant_observation_runs WHERE tenant_id=? AND idempotency_key=?",
                (tenant_id, validated["idempotency_key"]),
            ).fetchone()
            if existing:
                row = dict(existing)
                if str(row.get("request_fingerprint")) != fingerprint:
                    raise ObservationRunConflict("Idempotency key was already used for a different request.")
                output = self._public_run(row)
                output["idempotent_replay"] = True
                return output
            active = conn.execute(
                "SELECT run_id FROM tenant_observation_runs WHERE tenant_id=? AND watchlist_resource_id=? AND status IN ('queued','running') ORDER BY created_at DESC LIMIT 1",
                (tenant_id, watchlist_id),
            ).fetchone()
            if active:
                raise ObservationRunBusy(str(active["run_id"]))
            requested_symbols = list(plan.get("requested_symbols") or [])[:MAX_OBSERVATION_SYMBOLS]
            conn.execute(
                """
                INSERT INTO tenant_observation_runs (
                    run_id, tenant_id, owner_user_id, watchlist_resource_id, watchlist_name,
                    idempotency_key, request_fingerprint, status, interval, range_name,
                    max_symbols, requested_symbols_json, requested_count, provider_call_budget,
                    session_json, provider_plan_json, attempted_at, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    run_id, tenant_id, user_id, watchlist_id, str(plan.get("watchlist_name") or "")[:80],
                    validated["idempotency_key"], fingerprint, validated["interval"], validated["range"],
                    validated["max_symbols"], json_dumps(requested_symbols), len(requested_symbols),
                    min(int(_record(plan.get("provider_budget")).get("maximum_calls") or 0), MAX_OBSERVATION_PROVIDER_CALLS),
                    json_dumps(plan.get("session") or {}), json_dumps(plan), current, current, current,
                ),
            )
            self._audit(conn, tenant_id, user_id, run_id, "run-created", "", "queued", current, {"requested_count": len(requested_symbols)})
            row = conn.execute("SELECT * FROM tenant_observation_runs WHERE run_id=?", (run_id,)).fetchone()
        return self._public_run(dict(row))

    def get_run(self, context: dict[str, Any], run_id: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        if not _SAFE_RUN_ID.fullmatch(str(run_id or "")):
            return None
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM tenant_observation_runs WHERE tenant_id=? AND run_id=?", (tenant_id, run_id)).fetchone()
        return self._public_run(dict(row)) if row else None

    def list_runs(self, context: dict[str, Any], *, watchlist_id: str | None = None, limit: int = MAX_RUN_HISTORY) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        bounded = max(1, min(int(limit), MAX_RUN_HISTORY))
        with get_connection(self.db_path) as conn:
            if watchlist_id:
                rows = conn.execute(
                    "SELECT * FROM tenant_observation_runs WHERE tenant_id=? AND watchlist_resource_id=? ORDER BY rowid DESC LIMIT ?",
                    (tenant_id, str(watchlist_id), bounded),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tenant_observation_runs WHERE tenant_id=? ORDER BY rowid DESC LIMIT ?",
                    (tenant_id, bounded),
                ).fetchall()
        return [self._public_run(dict(row)) for row in rows]

    def start_run(self, context: dict[str, Any], run_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        current = _utc(now).isoformat()
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM tenant_observation_runs WHERE tenant_id=? AND run_id=?", (tenant_id, run_id)).fetchone()
            if not row:
                raise KeyError("Observation run not found.")
            existing = dict(row)
            if existing["status"] != "queued":
                return self._public_run(existing)
            if int(existing.get("cancellation_requested") or 0):
                conn.execute("UPDATE tenant_observation_runs SET status='cancelled', completed_at=?, updated_at=?, version=version+1 WHERE tenant_id=? AND run_id=?", (current, current, tenant_id, run_id))
                self._audit(conn, tenant_id, user_id, run_id, "run-cancelled", "queued", "cancelled", current)
            else:
                conn.execute("UPDATE tenant_observation_runs SET status='running', started_at=?, observation_started_at=?, updated_at=?, version=version+1 WHERE tenant_id=? AND run_id=?", (current, current, current, tenant_id, run_id))
                self._audit(conn, tenant_id, user_id, run_id, "run-started", "queued", "running", current)
            updated = conn.execute("SELECT * FROM tenant_observation_runs WHERE run_id=?", (run_id,)).fetchone()
        return self._public_run(dict(updated))

    def cancellation_requested(self, context: dict[str, Any], run_id: str) -> bool:
        tenant_id, _ = _require_authenticated(context)
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT cancellation_requested, status FROM tenant_observation_runs WHERE tenant_id=? AND run_id=?", (tenant_id, run_id)).fetchone()
        return bool(row and (int(row["cancellation_requested"]) or row["status"] == "cancelled"))

    def cancel_run(self, context: dict[str, Any], run_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        current = _utc(now).isoformat()
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM tenant_observation_runs WHERE tenant_id=? AND run_id=?", (tenant_id, run_id)).fetchone()
            if not row:
                raise KeyError("Observation run not found.")
            existing = dict(row)
            status = str(existing["status"])
            if status in _TERMINAL_STATUSES:
                return self._public_run(existing)
            next_status = "cancelled" if status == "queued" else status
            completed_at = current if next_status == "cancelled" else existing.get("completed_at")
            conn.execute(
                "UPDATE tenant_observation_runs SET cancellation_requested=1, status=?, completed_at=?, updated_at=?, version=version+1 WHERE tenant_id=? AND run_id=?",
                (next_status, completed_at, current, tenant_id, run_id),
            )
            self._audit(conn, tenant_id, user_id, run_id, "cancellation-requested", status, next_status, current)
            updated = conn.execute("SELECT * FROM tenant_observation_runs WHERE run_id=?", (run_id,)).fetchone()
        return self._public_run(dict(updated))

    def mark_cancelled(self, context: dict[str, Any], run_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        current = _utc(now).isoformat()
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT status FROM tenant_observation_runs WHERE tenant_id=? AND run_id=?", (tenant_id, run_id)).fetchone()
            if not row:
                raise KeyError("Observation run not found.")
            prior = str(row["status"])
            if prior not in _TERMINAL_STATUSES:
                conn.execute("UPDATE tenant_observation_runs SET cancellation_requested=1, status='cancelled', completed_at=?, updated_at=?, version=version+1 WHERE tenant_id=? AND run_id=?", (current, current, tenant_id, run_id))
                self._audit(conn, tenant_id, user_id, run_id, "run-cancelled", prior, "cancelled", current)
            updated = conn.execute("SELECT * FROM tenant_observation_runs WHERE run_id=?", (run_id,)).fetchone()
        return self._public_run(dict(updated))

    def fail_run(self, context: dict[str, Any], run_id: str, *, error_code: str, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        code = str(error_code or "run-failed").lower()
        if not _SAFE_ERROR.fullmatch(code):
            code = "run-failed"
        current = _utc(now).isoformat()
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT status, attempted_at FROM tenant_observation_runs WHERE tenant_id=? AND run_id=?", (tenant_id, run_id)).fetchone()
            if not row:
                raise KeyError("Observation run not found.")
            prior = str(row["status"])
            if prior not in _TERMINAL_STATUSES:
                attempted = _iso(row["attempted_at"])
                duration = max(0, int((_utc(now) - datetime.fromisoformat(attempted)).total_seconds() * 1000)) if attempted else 0
                conn.execute("UPDATE tenant_observation_runs SET status='failed', error_code=?, completed_at=?, duration_ms=?, updated_at=?, version=version+1 WHERE tenant_id=? AND run_id=?", (code, current, duration, current, tenant_id, run_id))
                self._audit(conn, tenant_id, user_id, run_id, "run-failed", prior, "failed", current, {"error_code": code})
            updated = conn.execute("SELECT * FROM tenant_observation_runs WHERE run_id=?", (run_id,)).fetchone()
        return self._public_run(dict(updated))

    def _validate_snapshot(self, row: dict[str, Any], requested: set[str], now: datetime) -> dict[str, Any]:
        if _contains_forbidden_key(row):
            raise ValueError("Provider output contains a private or forbidden field.")
        if len(json.dumps(row, ensure_ascii=False, default=str).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise ValueError("Provider snapshot exceeds the bounded payload size.")
        symbol = str(row.get("symbol") or "").upper()
        if symbol not in requested or not _SAFE_SYMBOL.fullmatch(symbol):
            raise ValueError("Provider output contains an unrequested symbol.")
        source_status = str(row.get("source_status") or "unavailable").lower()
        if source_status not in _SOURCE_STATUSES:
            raise ValueError("Provider output contains an unsupported source status.")
        observed_at = _iso(row.get("observed_at") or _record(row.get("quote")).get("market_data_as_of"))
        retrieved_at = _iso(row.get("retrieved_at") or row.get("fetched_at"))
        if not retrieved_at:
            raise ValueError("Provider output is missing a retrieval clock.")
        quote = _record(row.get("quote"))
        price = quote.get("last_price")
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise ValueError("Provider output is missing a valid market observation.")
        sources = []
        for source in _records(row.get("source_register"))[:12]:
            sources.append({
                "provider": str(source.get("provider") or "unknown")[:80],
                "source_url": _safe_url(source.get("source_url")),
                "source_status": str(source.get("source_status") or source_status)[:40],
                "observed_at": _iso(source.get("observed_at") or observed_at),
                "retrieved_at": _iso(source.get("retrieved_at") or retrieved_at),
            })
        payload = public_account_payload(copy.deepcopy(row))
        payload.update({"symbol": symbol, "observed_at": observed_at, "retrieved_at": retrieved_at, "source_status": source_status, "source_register": sources})
        encoded = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        if len(encoded) > MAX_SNAPSHOT_BYTES:
            raise ValueError("Sanitized provider snapshot exceeds the bounded payload size.")
        identity = _record(payload.get("identity"))
        primary = sources[0] if sources else {}
        return {
            "symbol": symbol,
            "asset_class": str(identity.get("asset_class") or "")[:24],
            "snapshot_status": "stale" if source_status == "stale" else "fresh",
            "source_status": source_status,
            "observed_at": observed_at,
            "retrieved_at": retrieved_at,
            "provider": str(primary.get("provider") or quote.get("provider") or "")[:80],
            "source_url": _safe_url(primary.get("source_url") or quote.get("source_url")),
            "confidence": float(payload.get("confidence")) if isinstance(payload.get("confidence"), (int, float)) else None,
            "payload": payload,
            "caveat": str(payload.get("caveat") or "")[:1_000],
            "data_gap": str(payload.get("data_gap") or "")[:1_000],
            "lkg_source_snapshot_id": None,
        }

    @staticmethod
    def _snapshot_from_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "snapshot_id": row.get("snapshot_id"),
            "run_id": row.get("run_id"),
            "watchlist_resource_id": row.get("watchlist_resource_id"),
            "symbol": row.get("symbol"),
            "asset_class": row.get("asset_class"),
            "snapshot_status": row.get("snapshot_status"),
            "source_status": row.get("source_status"),
            "observed_at": row.get("observed_at"),
            "retrieved_at": row.get("retrieved_at"),
            "provider": row.get("provider"),
            "source_url": row.get("source_url"),
            "confidence": row.get("confidence"),
            "payload": json_loads(row.get("payload_json"), {}),
            "caveat": row.get("caveat"),
            "data_gap": row.get("data_gap"),
            "lkg_source_snapshot_id": row.get("lkg_source_snapshot_id"),
            "created_at": row.get("created_at"),
        }

    def list_snapshots(self, context: dict[str, Any], run_id: str) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM tenant_observation_snapshots WHERE tenant_id=? AND run_id=? ORDER BY symbol", (tenant_id, run_id)).fetchall()
        return [public_account_payload(self._snapshot_from_row(dict(row))) for row in rows]

    def latest_last_known_good(self, context: dict[str, Any], watchlist_id: str, symbol: str) -> dict[str, Any] | None:
        tenant_id, _ = _require_authenticated(context)
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tenant_observation_snapshots WHERE tenant_id=? AND watchlist_resource_id=? AND symbol=? AND snapshot_status IN ('fresh','stale') ORDER BY created_at DESC, snapshot_id DESC LIMIT 1",
                (tenant_id, str(watchlist_id), str(symbol).upper()),
            ).fetchone()
        return public_account_payload(self._snapshot_from_row(dict(row))) if row else None

    def previous_rows(self, context: dict[str, Any], watchlist_id: str, symbols: list[str]) -> dict[str, dict[str, Any]]:
        return {
            symbol: snapshot["payload"]
            for symbol in symbols
            if (snapshot := self.latest_last_known_good(context, watchlist_id, symbol))
        }

    def quota_usage(self, context: dict[str, Any], *, now: datetime | None = None) -> dict[str, int]:
        tenant_id, _ = _require_authenticated(context)
        current = _utc(now)
        day_start = datetime.combine(current.date(), datetime.min.time(), tzinfo=timezone.utc).isoformat()
        window_start = (current - timedelta(minutes=1)).isoformat()
        with get_connection(self.db_path) as conn:
            alpha = conn.execute("SELECT COALESCE(SUM(call_count),0) AS count FROM tenant_provider_quota_ledger WHERE tenant_id=? AND provider='alpha-vantage' AND occurred_at>=?", (tenant_id, day_start)).fetchone()
            finnhub = conn.execute("SELECT COALESCE(SUM(call_count),0) AS count FROM tenant_provider_quota_ledger WHERE tenant_id=? AND provider='finnhub' AND occurred_at>=?", (tenant_id, window_start)).fetchone()
        return {"alpha_vantage_daily": int(alpha["count"]), "finnhub_window": int(finnhub["count"])}

    def commit_run(self, context: dict[str, Any], run_id: str, result: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, user_id = _require_authenticated(context)
        current_dt = _utc(now)
        current = current_dt.isoformat()
        if not isinstance(result, dict) or _contains_forbidden_key(result):
            raise ValueError("Invalid provider result envelope.")
        if len(json.dumps(result, ensure_ascii=False, default=str).encode("utf-8")) > MAX_OBSERVATION_PAYLOAD_BYTES:
            raise ValueError("Observation result exceeds the bounded payload size.")
        with get_connection(self.db_path) as conn:
            run_row = conn.execute("SELECT * FROM tenant_observation_runs WHERE tenant_id=? AND run_id=?", (tenant_id, run_id)).fetchone()
            if not run_row:
                raise KeyError("Observation run not found.")
            run = dict(run_row)
            if run["status"] != "running":
                return self._public_run(run)
            if int(run.get("cancellation_requested") or 0):
                conn.execute("UPDATE tenant_observation_runs SET status='cancelled', completed_at=?, updated_at=?, version=version+1 WHERE tenant_id=? AND run_id=?", (current, current, tenant_id, run_id))
                self._audit(conn, tenant_id, user_id, run_id, "run-cancelled", "running", "cancelled", current)
                updated = conn.execute("SELECT * FROM tenant_observation_runs WHERE run_id=?", (run_id,)).fetchone()
                return self._public_run(dict(updated))
            requested_list = [str(value).upper() for value in json_loads(run.get("requested_symbols_json"), [])]
            requested = set(requested_list)
            raw_rows = _records(result.get("rows"))
            if len(raw_rows) > len(requested):
                raise ValueError("Provider returned more rows than requested.")
            snapshots: dict[str, dict[str, Any]] = {}
            for raw in raw_rows:
                validated = self._validate_snapshot(raw, requested, current_dt)
                if validated["symbol"] in snapshots:
                    raise ValueError("Provider returned a duplicate symbol.")
                snapshots[validated["symbol"]] = validated
            missing = _records(result.get("missing_capabilities"))[:MAX_OBSERVATION_SYMBOLS * 4]
            for gap in missing:
                symbol = str(gap.get("symbol") or "").upper()
                if symbol and symbol not in requested:
                    raise ValueError("Missing-capability ledger contains an unrequested symbol.")
            lkg_reused = 0
            for symbol in requested_list:
                if symbol in snapshots:
                    continue
                prior = conn.execute(
                    "SELECT * FROM tenant_observation_snapshots WHERE tenant_id=? AND watchlist_resource_id=? AND symbol=? AND snapshot_status IN ('fresh','stale') ORDER BY created_at DESC, snapshot_id DESC LIMIT 1",
                    (tenant_id, run["watchlist_resource_id"], symbol),
                ).fetchone()
                if not prior:
                    continue
                prior_public = self._snapshot_from_row(dict(prior))
                payload = copy.deepcopy(prior_public["payload"])
                payload.update({
                    "status": "stale",
                    "source_status": "stale",
                    "observed_at": prior_public["observed_at"],
                    "retrieved_at": current,
                    "lkg_reused": True,
                    "caveat": (str(payload.get("caveat") or "") + "; provider refresh failed, so last-known-good evidence was retained.").strip("; "),
                    "data_gap": "Current provider observation unavailable; this row retains the prior valid market observation.",
                })
                for source in _records(payload.get("source_register")):
                    source["source_status"] = "stale"
                    source["retrieved_at"] = current
                snapshots[symbol] = {
                    "symbol": symbol,
                    "asset_class": prior_public["asset_class"],
                    "snapshot_status": "stale",
                    "source_status": "stale",
                    "observed_at": prior_public["observed_at"],
                    "retrieved_at": current,
                    "provider": prior_public["provider"],
                    "source_url": prior_public["source_url"],
                    "confidence": prior_public["confidence"],
                    "payload": payload,
                    "caveat": str(payload.get("caveat") or "")[:1_000],
                    "data_gap": str(payload.get("data_gap") or "")[:1_000],
                    "lkg_source_snapshot_id": prior_public["snapshot_id"],
                }
                lkg_reused += 1
            budget = _record(result.get("provider_budget"))
            actual_calls = max(0, int(budget.get("actual_calls") or 0))
            if actual_calls > MAX_OBSERVATION_PROVIDER_CALLS:
                raise ValueError("Provider result exceeded the call budget.")
            fresh_count = sum(row["lkg_source_snapshot_id"] is None for row in snapshots.values())
            failed_count = max(0, len(requested_list) - fresh_count)
            status = "completed" if fresh_count == len(requested_list) and not missing else "partial" if snapshots else "failed"
            prior_run = conn.execute(
                "SELECT * FROM tenant_observation_runs WHERE tenant_id=? AND watchlist_resource_id=? AND run_id<>? AND status IN ('completed','partial') ORDER BY completed_at DESC, run_id DESC LIMIT 1",
                (tenant_id, run["watchlist_resource_id"], run_id),
            ).fetchone()
            previous_payloads: list[dict[str, Any]] = []
            if prior_run:
                prior_snapshots = conn.execute("SELECT payload_json FROM tenant_observation_snapshots WHERE tenant_id=? AND run_id=? ORDER BY symbol", (tenant_id, prior_run["run_id"])).fetchall()
                previous_payloads = [json_loads(row["payload_json"], {}) for row in prior_snapshots]
            current_payloads = [snapshots[symbol]["payload"] for symbol in requested_list if symbol in snapshots]
            diff = build_research_snapshot_diff(
                {"job_id": prior_run["run_id"], "list_id": run["watchlist_resource_id"], "status": "completed", "rows": previous_payloads, "completed_at": prior_run["completed_at"]} if prior_run else None,
                {"job_id": run_id, "list_id": run["watchlist_resource_id"], "status": "completed", "rows": current_payloads, "completed_at": current},
                now=current_dt,
            )
            for symbol in requested_list:
                snapshot = snapshots.get(symbol)
                if not snapshot:
                    continue
                snapshot_id = f"obssnap_{_hash([run_id, symbol])[:20]}"
                payload_json = json_dumps(snapshot["payload"])
                conn.execute(
                    """
                    INSERT INTO tenant_observation_snapshots (
                        snapshot_id, tenant_id, owner_user_id, run_id, watchlist_resource_id,
                        symbol, asset_class, snapshot_status, source_status, observed_at,
                        retrieved_at, provider, source_url, confidence, content_hash,
                        payload_json, caveat, data_gap, lkg_source_snapshot_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id, tenant_id, user_id, run_id, run["watchlist_resource_id"],
                        symbol, snapshot["asset_class"], snapshot["snapshot_status"], snapshot["source_status"],
                        snapshot["observed_at"], snapshot["retrieved_at"], snapshot["provider"], snapshot["source_url"],
                        snapshot["confidence"], _hash(snapshot["payload"]), payload_json, snapshot["caveat"],
                        snapshot["data_gap"], snapshot["lkg_source_snapshot_id"], current,
                    ),
                )
            actual_by_operation = _record(budget.get("actual_calls_by_operation"))
            provider_states = _records(result.get("provider_states"))[:16]
            state_by_operation = {f"{row.get('provider')}:{row.get('operation')}": str(row.get("source_status") or "unavailable") for row in provider_states}
            for operation, calls in actual_by_operation.items():
                call_count = max(0, min(int(calls or 0), MAX_OBSERVATION_PROVIDER_CALLS))
                if not call_count:
                    continue
                provider = str(operation).split(":", 1)[0]
                conn.execute(
                    "INSERT INTO tenant_provider_quota_ledger (event_id, tenant_id, owner_user_id, run_id, provider, operation, call_count, source_status, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (new_id("opq"), tenant_id, user_id, run_id, provider, str(operation)[:80], call_count, state_by_operation.get(str(operation), "contacted"), current),
                )
            observed = [row["observed_at"] for row in snapshots.values() if row.get("observed_at")]
            retrieved = [row["retrieved_at"] for row in snapshots.values() if row.get("retrieved_at")]
            attempted = _iso(run.get("attempted_at"))
            duration = max(0, int((current_dt - datetime.fromisoformat(attempted)).total_seconds() * 1000)) if attempted else 0
            conn.execute(
                """
                UPDATE tenant_observation_runs SET
                    status=?, completed_count=?, failed_count=?, skipped_count=?, lkg_reused_count=?,
                    provider_call_count=?, cache_hits=?, stale_hits=?, provider_states_json=?,
                    missing_capabilities_json=?, diff_json=?, observation_ended_at=?, retrieved_at=?,
                    completed_at=?, duration_ms=?, error_code=?, updated_at=?, version=version+1
                WHERE tenant_id=? AND run_id=?
                """,
                (
                    status, len(snapshots), failed_count, max(0, len(requested_list) - len(snapshots)), lkg_reused,
                    actual_calls, max(0, int(budget.get("cache_hits") or 0)), max(0, int(budget.get("stale_hits") or 0)),
                    json_dumps(provider_states), json_dumps(missing), json_dumps(diff), max(observed) if observed else current,
                    max(retrieved) if retrieved else current, current, duration, "" if status != "failed" else "no-valid-observation",
                    current, tenant_id, run_id,
                ),
            )
            self._audit(conn, tenant_id, user_id, run_id, "run-committed", "running", status, current, {"completed_count": len(snapshots), "failed_count": failed_count, "lkg_reused_count": lkg_reused})
            updated = conn.execute("SELECT * FROM tenant_observation_runs WHERE run_id=?", (run_id,)).fetchone()
        return self._public_run(dict(updated))

    def list_audit(self, context: dict[str, Any], *, run_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        tenant_id, _ = _require_authenticated(context)
        bounded = max(1, min(int(limit), 100))
        with get_connection(self.db_path) as conn:
            if run_id:
                rows = conn.execute("SELECT event_id, run_id, event_type, prior_status, new_status, created_at FROM tenant_observation_run_audit WHERE tenant_id=? AND run_id=? ORDER BY created_at DESC LIMIT ?", (tenant_id, run_id, bounded)).fetchall()
            else:
                rows = conn.execute("SELECT event_id, run_id, event_type, prior_status, new_status, created_at FROM tenant_observation_run_audit WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?", (tenant_id, bounded)).fetchall()
        return [dict(row) for row in rows]

    def build_attention_context(self, context: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id, _ = _require_authenticated(context)
        with get_connection(self.db_path) as conn:
            latest = conn.execute("SELECT * FROM tenant_observation_runs WHERE tenant_id=? AND status IN ('completed','partial','cancelled','failed') ORDER BY rowid DESC LIMIT 1", (tenant_id,)).fetchone()
            active = conn.execute("SELECT * FROM tenant_observation_runs WHERE tenant_id=? AND status IN ('queued','running') ORDER BY rowid DESC LIMIT 1", (tenant_id,)).fetchone()
            watchlist = conn.execute(
                "SELECT w.resource_id, w.name, COUNT(i.resource_id) AS item_count FROM tenant_watchlists w LEFT JOIN tenant_watchlist_items i ON i.tenant_id=w.tenant_id AND i.watchlist_resource_id=w.resource_id AND i.active=1 WHERE w.tenant_id=? AND w.active=1 GROUP BY w.resource_id, w.name ORDER BY w.updated_at DESC LIMIT 1",
                (tenant_id,),
            ).fetchone()
        latest_public = self._public_run(dict(latest)) if latest else _empty_run("not-run")
        active_public = self._public_run(dict(active)) if active else None
        diff = _record(latest_public.get("diff"))
        changes = _records(diff.get("changes"))
        available = {"resource_id": watchlist["resource_id"], "name": watchlist["name"], "item_count": int(watchlist["item_count"])} if watchlist else None
        return public_account_payload({
            "observation_run_version": OBSERVATION_RUN_VERSION,
            "mode": "account-local",
            "latest_run": latest_public,
            "active_run": active_public,
            "available_watchlist": available,
            "changes": changes,
            "material_change_count": sum(str(row.get("severity") or "info") in {"material", "high", "critical"} for row in changes),
            "source_health": latest_public.get("provider_states") or [],
            "refresh_action": {
                "enabled": bool(available and not active_public),
                "endpoint": "/api/account/observation-runs",
                "reason": "ready" if available and not active_public else "active-run" if active_public else "no-saved-watchlist",
                "maximum_symbols": MAX_OBSERVATION_SYMBOLS,
                "maximum_provider_calls": MAX_OBSERVATION_PROVIDER_CALLS,
            },
            "provider_call_count": 0,
            "generated_at": _utc(now).isoformat(),
            "caveat": "Attention reads committed observation runs only and does not contact market providers.",
            "not_financial_advice": True,
        })

    @staticmethod
    def _public_run(row: dict[str, Any]) -> dict[str, Any]:
        if not row:
            return _empty_run("not-run")
        plan = json_loads(row.get("provider_plan_json"), {})
        provider_budget = _record(plan.get("provider_budget"))
        provider_budget.update({
            "actual_calls": int(row.get("provider_call_count") or 0),
            "cache_hits": int(row.get("cache_hits") or 0),
            "stale_hits": int(row.get("stale_hits") or 0),
        })
        return public_account_payload({
            "observation_run_version": OBSERVATION_RUN_VERSION,
            "mode": "account-local",
            "run_id": row.get("run_id"),
            "watchlist_resource_id": row.get("watchlist_resource_id"),
            "watchlist_name": row.get("watchlist_name"),
            "status": row.get("status"),
            "interval": row.get("interval"),
            "range": row.get("range_name"),
            "requested_symbols": json_loads(row.get("requested_symbols_json"), []),
            "requested_count": int(row.get("requested_count") or 0),
            "completed_count": int(row.get("completed_count") or 0),
            "failed_count": int(row.get("failed_count") or 0),
            "skipped_count": int(row.get("skipped_count") or 0),
            "lkg_reused_count": int(row.get("lkg_reused_count") or 0),
            "provider_call_budget": int(row.get("provider_call_budget") or 0),
            "provider_call_count": int(row.get("provider_call_count") or 0),
            "provider_budget": provider_budget,
            "session": json_loads(row.get("session_json"), {}),
            "symbol_plan": plan.get("symbol_plan") or [],
            "skipped_capabilities": plan.get("skipped_capabilities") or [],
            "provider_states": json_loads(row.get("provider_states_json"), []),
            "missing_capabilities": json_loads(row.get("missing_capabilities_json"), []),
            "diff": json_loads(row.get("diff_json"), {}),
            "cancellation_requested": bool(row.get("cancellation_requested")),
            "attempted_at": row.get("attempted_at"),
            "started_at": row.get("started_at"),
            "observation_started_at": row.get("observation_started_at"),
            "observation_ended_at": row.get("observation_ended_at"),
            "retrieved_at": row.get("retrieved_at"),
            "completed_at": row.get("completed_at"),
            "duration_ms": int(row.get("duration_ms") or 0),
            "error_code": row.get("error_code") or None,
            "version": int(row.get("version") or 1),
            "not_financial_advice": True,
        })


def _empty_run(status: str) -> dict[str, Any]:
    return {
        "observation_run_version": OBSERVATION_RUN_VERSION,
        "mode": "account-local",
        "run_id": None,
        "status": status,
        "requested_count": 0,
        "completed_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "lkg_reused_count": 0,
        "provider_call_budget": MAX_OBSERVATION_PROVIDER_CALLS,
        "provider_call_count": 0,
        "provider_budget": {"maximum_calls": MAX_OBSERVATION_PROVIDER_CALLS, "actual_calls": 0},
        "provider_states": [],
        "missing_capabilities": [],
        "diff": {},
        "not_financial_advice": True,
    }


def build_fixture_observation_context() -> dict[str, Any]:
    return {
        "observation_run_version": OBSERVATION_RUN_VERSION,
        "mode": "fixture",
        "latest_run": {
            "mode": "fixture",
            "run_id": "fixture-observation-run",
            "watchlist_name": "Daily Radar",
            "status": "completed",
            "requested_count": 5,
            "completed_count": 5,
            "provider_call_count": 0,
            "provider_budget": {"maximum_calls": MAX_OBSERVATION_PROVIDER_CALLS, "actual_calls": 0},
            "completed_at": "2026-07-03T12:00:02+00:00",
            "session": {"policy": "fixture", "calendar_status": "fixture", "market_open_claimed": False},
        },
        "active_run": None,
        "available_watchlist": {"resource_id": "fixture-daily-radar", "name": "Daily Radar", "item_count": 5},
        "changes": [],
        "material_change_count": 0,
        "source_health": [],
        "refresh_action": {"enabled": False, "reason": "fixture-does-not-contact-providers", "maximum_symbols": 5, "maximum_provider_calls": 16},
        "provider_call_count": 0,
        "generated_at": "2026-07-03T12:00:02+00:00",
        "caveat": "Deterministic; no provider contact.",
        "not_financial_advice": True,
    }


class SourceBackedObservationAdapter:
    """Reuse existing source/cache engines without making Attention a fetch surface."""

    @staticmethod
    def _gap(provider: str, status: str, reason: str) -> dict[str, Any]:
        return {"provider": provider, "source_url": "", "source_status": status, "data_gap": reason, "rows": [], "metrics": {}}

    def observe(self, watchlist: dict[str, Any], plan: dict[str, Any], *, previous_rows: dict[str, dict[str, Any]], cancellation_requested: Callable[[], bool]) -> dict[str, Any]:
        from .watchlist_desk import _prime_history_batch

        started = _utc()
        item_by_symbol = {str(item.get("symbol") or "").upper(): item for item in _records(watchlist.get("items"))}
        symbol_plan = {str(row.get("symbol") or "").upper(): row for row in _records(plan.get("symbol_plan"))}
        identities: list[dict[str, Any]] = []
        for symbol in list(plan.get("requested_symbols") or []):
            item = item_by_symbol.get(symbol) or {}
            identity = resolve_symbol(symbol, asset_class=str(item.get("asset_class") or "equity"))
            if identity:
                identities.append(identity)
        due_identities = [identity for identity in identities if _record(symbol_plan.get(str(identity["symbol"]))).get("due_mode") == "provider-refresh"]
        history_rows: list[dict[str, Any]] = []
        history_calls = 0
        if due_identities and not cancellation_requested():
            history_result = _prime_history_batch(due_identities, interval="1d", range_name=str(_record(plan.get("request")).get("range") or "3mo"))
            history_rows = _records(history_result.get("rows"))
            history_calls = min(int(history_result.get("provider_call_count") or 0), 1)
        history_state = {str(row.get("symbol") or "").upper(): row for row in history_rows}
        histories: dict[str, list[dict[str, Any]]] = {}
        for identity in identities:
            symbol = str(identity["symbol"])
            record = load_runtime_cache_record(history_cache_key(str(identity.get("asset_class") or "equity"), symbol, "1d", str(_record(plan.get("request")).get("range") or "3mo")))
            if record and isinstance(record.data, list) and record.data:
                histories[symbol] = [dict(row) for row in record.data if isinstance(row, dict)]
        planned = _record(_record(plan.get("provider_budget")).get("planned_calls_by_operation"))
        remaining = {key: max(0, int(value or 0)) for key, value in planned.items()}
        asset_by_symbol = {str(identity["symbol"]): str(identity.get("asset_class") or "equity") for identity in identities}

        def guarded(fetcher: Callable[[str], dict[str, Any]], operation: str, provider: str) -> Callable[[str], dict[str, Any]]:
            def run(symbol: str) -> dict[str, Any]:
                if cancellation_requested():
                    return self._gap(provider, "cancelled", "Observation run was cancelled before this capability.")
                if asset_by_symbol.get(symbol) not in {"equity", "etf", "index"}:
                    return self._gap(provider, "not_applicable", "Capability is not applicable to this asset class.")
                if remaining.get(operation, 0) <= 0:
                    return self._gap(provider, "quota-deferred", "Capability was skipped by the session/quota plan.")
                remaining[operation] -= 1
                return fetcher(symbol)
            return run

        research = build_research_snapshot_rows(
            [identity for identity in identities if histories.get(str(identity["symbol"]))],
            histories,
            overview_fetcher=guarded(fetch_alpha_vantage_overview, "alpha-vantage:overview", "alpha-vantage"),
            earnings_fetcher=guarded(fetch_finnhub_earnings_calendar, "finnhub:earnings-calendar", "finnhub"),
            news_fetcher=guarded(fetch_finnhub_company_news, "finnhub:company-news", "finnhub"),
            previous_rows=previous_rows,
            history_call_count=history_calls,
            max_symbols=max(1, len(identities)),
            now=started,
        ) if identities else {"rows": [], "provider_budget": {"maximum_calls": 16, "actual_calls": history_calls, "actual_calls_by_operation": {"yfinance:multi-history": history_calls}, "cache_hits": 0, "stale_hits": 0, "failed_calls": 0, "blocked_calls": 0, "skipped_calls": 0}}
        rows = []
        for row in _records(research.get("rows")):
            symbol = str(row.get("symbol") or "").upper()
            quote = _record(row.get("quote"))
            retrieved = _iso(row.get("fetched_at")) or started.isoformat()
            observed = _iso(quote.get("market_data_as_of"))
            history_meta = history_state.get(symbol) or {}
            source_register = _records(row.get("source_register"))
            source_register.insert(0, {
                "provider": "yfinance",
                "source_url": f"https://finance.yahoo.com/quote/{symbol}",
                "source_status": history_meta.get("source_status") or ("cached" if symbol in histories else "unavailable"),
                "observed_at": observed,
                "retrieved_at": _iso(history_meta.get("fetched_at")) or retrieved,
            })
            rows.append({**row, "observed_at": observed, "retrieved_at": retrieved, "source_register": source_register})
        completed_symbols = {str(row.get("symbol") or "").upper() for row in rows}
        missing = []
        for symbol in list(plan.get("requested_symbols") or []):
            if symbol in completed_symbols:
                continue
            source = history_state.get(symbol) or {}
            missing.append({
                "symbol": symbol,
                "provider": "yfinance",
                "capability": "history",
                "source_status": source.get("source_status") or "unavailable",
                "reason": source.get("data_gap") or "No valid exact-symbol history was available under the run policy.",
            })
        budget = _record(research.get("provider_budget"))
        budget["maximum_calls"] = MAX_OBSERVATION_PROVIDER_CALLS
        actual_by_operation = _record(budget.get("actual_calls_by_operation"))
        bounded_actual: dict[str, int] = {}
        for operation in ("yfinance:multi-history", "alpha-vantage:overview", "finnhub:earnings-calendar", "finnhub:company-news"):
            bounded_actual[operation] = min(
                max(0, int(actual_by_operation.get(operation) or 0)),
                max(0, int(planned.get(operation) or 0)),
            )
        budget["actual_calls_by_operation"] = bounded_actual
        budget["actual_calls"] = min(sum(bounded_actual.values()), MAX_OBSERVATION_PROVIDER_CALLS)
        states = []
        for operation in ("yfinance:multi-history", "alpha-vantage:overview", "finnhub:earnings-calendar", "finnhub:company-news"):
            provider, capability = operation.split(":", 1)
            actual = int(bounded_actual.get(operation) or 0)
            states.append({
                "provider": provider,
                "operation": capability,
                "configured": provider == "yfinance" or bool(get_settings().alphavantage_api_key if provider == "alpha-vantage" else get_settings().finnhub_api_key),
                "contacted": actual > 0,
                "source_status": "contacted" if actual else "cached-or-skipped",
            })
        return {"rows": rows, "provider_budget": budget, "provider_states": states, "missing_capabilities": missing}


class ObservationRunCoordinator:
    def __init__(
        self,
        store: ObservationRunStore,
        watchlist_loader: Callable[[dict[str, Any], str], dict[str, Any] | None],
        *,
        adapter: Any | None = None,
        execute_inline: bool = False,
        completion_callback: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None,
    ):
        self.store = store
        self.watchlist_loader = watchlist_loader
        self.adapter = adapter or SourceBackedObservationAdapter()
        self.execute_inline = bool(execute_inline)
        self.completion_callback = completion_callback
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def submit(self, context: dict[str, Any], body: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        validated = validate_observation_request(body)
        watchlist_id = validated.get("watchlist_id")
        if not watchlist_id:
            raise ValueError("watchlist_id is required.")
        watchlist = self.watchlist_loader(context, watchlist_id)
        if not watchlist:
            raise KeyError("Saved Watchlist not found.")
        plan = build_observation_run_plan(context, watchlist, validated, quota_usage=self.store.quota_usage(context, now=now), now=now)
        run = self.store.create_run(context, watchlist, validated, plan, now=now)
        if run.get("idempotent_replay"):
            return run
        if self.execute_inline:
            return self._execute(context, watchlist, plan, now=now)
        thread = threading.Thread(target=self._execute, args=(copy.deepcopy(context), copy.deepcopy(watchlist), copy.deepcopy(plan)), kwargs={"now": None}, daemon=True, name=f"observation-{run['run_id'][-8:]}")
        with self._lock:
            self._threads[str(run["run_id"])] = thread
        thread.start()
        return run

    def _execute(self, context: dict[str, Any], watchlist: dict[str, Any], plan: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        run_id = str(plan["run_id"])
        result: dict[str, Any]
        try:
            started = self.store.start_run(context, run_id, now=now)
            if started["status"] == "cancelled":
                result = started
            else:
                previous = self.store.previous_rows(context, str(plan["watchlist_resource_id"]), list(plan.get("requested_symbols") or []))
                observed = self.adapter.observe(
                    watchlist,
                    plan,
                    previous_rows=previous,
                    cancellation_requested=lambda: self.store.cancellation_requested(context, run_id),
                )
                if self.store.cancellation_requested(context, run_id):
                    result = self.store.mark_cancelled(context, run_id, now=now)
                else:
                    result = self.store.commit_run(context, run_id, observed, now=now)
        except ValueError:
            result = self.store.fail_run(context, run_id, error_code="provider-output-invalid", now=now)
        except Exception:
            result = self.store.fail_run(context, run_id, error_code="provider-runtime-error", now=now)
        finally:
            with self._lock:
                self._threads.pop(run_id, None)
        if self.completion_callback is not None:
            try:
                self.completion_callback(context, result)
            except Exception:
                # Observation evidence is already committed locally. Hosted
                # continuity is best-effort and reports its own degraded state.
                pass
        return result

    def cancel(self, context: dict[str, Any], run_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        return self.store.cancel_run(context, run_id, now=now)
