from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

from .research_workspace_db import execute_query, json_dumps, json_loads, new_id
from .symbol_intelligence import build_symbol_delivery_contract
from .symbol_workstation import resolve_symbol


RESEARCH_OPERATIONS_VERSION = "research_operations.v1"
ALLOWED_REFRESH_PANELS = (
    "chart-core",
    "technicals",
    "financials",
    "catalysts",
    "news",
    "sources",
    "comparison",
)
DEFAULT_REFRESH_PANELS = (
    "chart-core",
    "financials",
    "catalysts",
    "sources",
)
MAX_EXACT_REFRESH_CALLS = 8
MAX_JOB_EVENTS = 20
MAX_PUBLIC_JOBS = 20
MAX_OPERATIONS_HISTORY = 5
MAX_PUBLIC_OBSERVATIONS = 100
ACTIVE_JOB_STATUSES = {"queued", "running"}
SUCCESS_STATUSES = {"live/fresh", "cached", "official/materialized"}
FAILURE_STATUSES = {
    "provider-error",
    "unavailable",
    "forbidden",
    "forbidden/subscription-blocked",
}
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9=._-]{0,23}$")
_IDEMPOTENCY = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")

PANEL_SLO_POLICY: dict[str, dict[str, int | None]] = {
    "chart-core": {"retrieval_target_seconds": 900, "observation_target_seconds": 900},
    "technicals": {"retrieval_target_seconds": 900, "observation_target_seconds": 900},
    "financials": {"retrieval_target_seconds": 86_400, "observation_target_seconds": None},
    "catalysts": {"retrieval_target_seconds": 900, "observation_target_seconds": 86_400},
    "news": {"retrieval_target_seconds": 900, "observation_target_seconds": 86_400},
    "sources": {"retrieval_target_seconds": 900, "observation_target_seconds": None},
    "comparison": {"retrieval_target_seconds": 900, "observation_target_seconds": 900},
}

PANEL_OPERATION_PLANS: dict[str, tuple[str, ...]] = {
    "chart-core": ("yfinance:history",),
    "technicals": ("yfinance:history",),
    "financials": (
        "yfinance:financials",
        "sec:company-ticker",
        "sec:companyfacts",
        "alpha-vantage:overview",
        "finnhub:profile",
        "alpha-vantage:earnings",
        "finnhub:earnings",
    ),
    "catalysts": (),
    "news": (
        "yfinance:news",
        "alpha-vantage:news",
        "finnhub:news",
    ),
    "sources": (),
    "comparison": ("yfinance:primary-history", "yfinance:comparison-history"),
}

_PRIVATE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "credential",
    "credentials",
    "local_path",
    "notes",
    "password",
    "private_notes",
    "provider_body",
    "raw_body",
    "secret",
    "token",
    "watch_reason",
}


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _iso(value: datetime | str | None) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return _utc(value).replace(microsecond=0).isoformat()
    parsed = _parse_time(value)
    return parsed.replace(microsecond=0).isoformat() if parsed else None


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _utc(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.fromisoformat(f"{text}T00:00:00+00:00")
        except ValueError:
            return None
    return _utc(parsed)


def _age_seconds(value: Any, now: datetime) -> int | None:
    parsed = _parse_time(value)
    return max(0, int((now - parsed).total_seconds())) if parsed else None


def _safe_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = urlparse(text)
    except ValueError:
        return None
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _public(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _public(item)
            for key, item in value.items()
            if str(key).lower() not in _PRIVATE_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_public(item) for item in value]
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, Path):
        return "[redacted]"
    if isinstance(value, str):
        lowered = value.lower()
        if re.match(r"^[a-z]:\\", value, flags=re.IGNORECASE):
            return "[redacted]"
        if any(marker in lowered for marker in ("bearer ", "sk-", "aiza")):
            return "[redacted]"
        return value[:1_000]
    return value


def _records(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value or [] if isinstance(row, dict)]


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_status(value: Any) -> str:
    status = str(value or "unavailable").strip().lower().replace("_", "-")
    aliases = {
        "available": "live/fresh",
        "fresh": "live/fresh",
        "ok": "live/fresh",
        "missing-key": "missing-key",
        "missing key": "missing-key",
        "rate limited": "rate-limited",
        "provider error": "provider-error",
        "official-filing-fact": "official/materialized",
    }
    return aliases.get(status, status)


def classify_panel_freshness(
    panel: str,
    *,
    retrieved_at: datetime | str | None,
    observed_at: datetime | str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if panel not in PANEL_SLO_POLICY:
        raise ValueError(f"Unsupported panel freshness policy: {panel}")
    current = _utc(now)
    policy = PANEL_SLO_POLICY[panel]
    retrieval_age = _age_seconds(retrieved_at, current)
    observation_age = _age_seconds(observed_at, current)
    retrieval_target = int(policy["retrieval_target_seconds"] or 0)
    observation_target = policy["observation_target_seconds"]

    retrieval_state = (
        "unavailable"
        if retrieval_age is None
        else "within-slo"
        if retrieval_age <= retrieval_target
        else "aging"
        if retrieval_age <= retrieval_target * 2
        else "stale"
    )
    observation_state = (
        "not-applicable"
        if observation_target is None
        else "unavailable"
        if observation_age is None
        else "within-slo"
        if observation_age <= int(observation_target)
        else "stale"
    )
    if retrieval_state == "unavailable":
        overall = "unavailable"
    elif "stale" in {retrieval_state, observation_state}:
        overall = "stale"
    elif observation_state == "unavailable":
        overall = "unavailable"
    elif retrieval_state == "aging":
        overall = "aging"
    else:
        overall = "within-slo"
    return {
        "panel": panel,
        "retrieved_at": _iso(retrieved_at),
        "observed_at": _iso(observed_at),
        "retrieval_age_seconds": retrieval_age,
        "observation_age_seconds": observation_age,
        "retrieval_target_seconds": retrieval_target,
        "observation_target_seconds": observation_target,
        "retrieval_slo_state": retrieval_state,
        "observation_slo_state": observation_state,
        "slo_state": overall,
        "session_aware": False,
        "caveat": (
            "Retrieval and market/event observation clocks are evaluated "
            "separately; the current SLO policy is not market-session aware."
        ),
    }


def _normalize_panels(panels: Iterable[Any] | None) -> list[str]:
    supplied = list(panels or DEFAULT_REFRESH_PANELS)
    result: list[str] = []
    for value in supplied:
        panel = str(value or "").strip().lower()
        if panel not in ALLOWED_REFRESH_PANELS:
            raise ValueError(f"Unsupported exact refresh panel: {panel or value}")
        if panel not in result:
            result.append(panel)
    if not result:
        raise ValueError("At least one exact refresh panel is required.")
    return result


def plan_refresh_budget(
    panels: Iterable[Any] | None,
    *,
    asset_class: str = "equity",
) -> dict[str, Any]:
    normalized = _normalize_panels(panels)
    resolved_class = str(asset_class or "equity").lower()
    operations: dict[str, list[str]] = {}
    for panel in normalized:
        selected = list(PANEL_OPERATION_PLANS[panel])
        if resolved_class == "crypto" and panel == "financials":
            selected = []
        operations[panel] = selected
    planned = sum(len(rows) for rows in operations.values())
    if planned > MAX_EXACT_REFRESH_CALLS:
        raise ValueError(
            f"Exact refresh provider-call ceiling exceeded: {planned} > "
            f"{MAX_EXACT_REFRESH_CALLS}."
        )
    return {
        "hard_ceiling": MAX_EXACT_REFRESH_CALLS,
        "planned_calls": planned,
        "planned_by_panel": {
            panel: len(rows) for panel, rows in operations.items()
        },
        "planned_operations": operations,
        "actual_calls": 0,
        "cache_hits": 0,
        "stale_hits": 0,
        "failed_calls": 0,
        "rate_limited_calls": 0,
        "skipped_calls": 0,
        "broad_universe_fanout": False,
        "watchlist_refresh_provider_call_ceiling": 16,
        "accounting_method": "normalized-provider-operation-evidence",
        "caveat": (
            "Counts are bounded logical provider operations, not exchange "
            "wire messages or streaming ticks."
        ),
    }


def build_refresh_request(
    symbol: str,
    *,
    asset_class: str = "equity",
    interval: str = "1d",
    range_name: str = "3mo",
    panels: Iterable[Any] | None = None,
    runtime_mode: str = "live-if-available",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    normalized_symbol = str(symbol or "").strip().upper()
    if not _SYMBOL.fullmatch(normalized_symbol):
        raise ValueError("Invalid exact refresh symbol.")
    normalized_panels = _normalize_panels(panels)
    normalized_class = str(asset_class or "equity").strip().lower()
    normalized_interval = str(interval or "1d").strip().lower()
    normalized_range = str(range_name or "3mo").strip().lower()
    if not re.fullmatch(r"[a-z0-9]{1,8}", normalized_interval):
        raise ValueError("Invalid exact refresh interval.")
    if not re.fullmatch(r"[a-z0-9]{1,8}", normalized_range):
        raise ValueError("Invalid exact refresh range.")
    budget = plan_refresh_budget(normalized_panels, asset_class=normalized_class)
    key = str(idempotency_key or "").strip()
    if key and not _IDEMPOTENCY.fullmatch(key):
        raise ValueError("Invalid idempotency key.")
    fingerprint_basis = {
        "symbol": normalized_symbol,
        "asset_class": normalized_class,
        "interval": normalized_interval,
        "range": normalized_range,
        "panels": normalized_panels,
        "runtime_mode": "live-if-available",
        "version": RESEARCH_OPERATIONS_VERSION,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_basis,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:24]
    nonce = key or uuid.uuid4().hex[:12]
    request_id = hashlib.sha256(f"{fingerprint}:{nonce}".encode()).hexdigest()[:24]
    return {
        "request_id": request_id,
        "request_fingerprint": fingerprint,
        "idempotency_key": key or None,
        "symbol": normalized_symbol,
        "asset_class": normalized_class,
        "interval": normalized_interval,
        "range": normalized_range,
        "panels": normalized_panels,
        "runtime_mode": (
            "live-if-available"
            if runtime_mode != "fixture"
            else "fixture"
        ),
        "budget": budget,
        "not_financial_advice": True,
    }


def configured_provider_names() -> list[str]:
    variables = {
        "Alpha Vantage": "ALPHAVANTAGE_API_KEY",
        "Finnhub": "FINNHUB_API_KEY",
        "Gemini": "GEMINI_API_KEY",
        "OpenSky": "OPENSKY_CLIENT_ID",
        "SEC EDGAR": "SEC_USER_AGENT",
    }
    return sorted(name for name, variable in variables.items() if os.getenv(variable))


def build_observed_provider_health(
    observations: Iterable[dict[str, Any]] | None,
    *,
    configured_providers: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for raw in observations or []:
        if not isinstance(raw, dict):
            continue
        provider = str(raw.get("provider") or "").strip()
        if not provider:
            continue
        current = dict(raw)
        prior = latest.get(provider)
        if prior is None or str(current.get("retrieved_at") or "") >= str(
            prior.get("retrieved_at") or ""
        ):
            latest[provider] = current
    output: list[dict[str, Any]] = []
    configured = {str(value) for value in configured_providers or [] if value}
    for provider, raw in sorted(latest.items()):
        status = _normalize_status(raw.get("source_status") or raw.get("status"))
        contacted = bool(raw.get("contacted", True))
        successful = bool(
            raw.get(
                "successful",
                status in SUCCESS_STATUSES or status == "stale",
            )
        )
        availability = (
            "available"
            if status in SUCCESS_STATUSES
            else "limited"
            if status in {"stale", "rate-limited", "proxy/static"}
            else "unavailable"
        )
        output.append(
            {
                "provider": provider,
                "panel": raw.get("panel"),
                "status": status,
                "configured": provider in configured,
                "contacted": contacted,
                "successful": successful,
                "availability": availability,
                "source": raw.get("source") or "",
                "source_url": _safe_url(raw.get("source_url")),
                "fetched_at": _iso(
                    raw.get("retrieved_at") or raw.get("fetched_at")
                ),
                "row_count": raw.get("row_count"),
                "cached": status == "cached",
                "caveat": raw.get("caveat") or "",
                "data_gap": raw.get("data_gap"),
                "evidence_basis": "observed-panel-delivery",
            }
        )
    observed = set(latest)
    for provider in sorted(configured - observed):
        output.append(
            {
                "provider": provider,
                "panel": None,
                "status": "configured",
                "configured": True,
                "contacted": False,
                "successful": False,
                "availability": "unavailable",
                "source": "environment-presence-only",
                "source_url": None,
                "fetched_at": None,
                "row_count": None,
                "cached": False,
                "caveat": (
                    "Credential presence is known, but no successful provider "
                    "contact is inferred."
                ),
                "data_gap": "No bounded panel observation is recorded.",
                "evidence_basis": "configuration-presence-only",
            }
        )
    return _public(output)


class ResearchOperationsStore:
    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        max_jobs: int = 50,
        max_observations: int = 250,
    ) -> None:
        self.db_path = db_path
        self.max_jobs = max(1, min(int(max_jobs), 100))
        self.max_observations = max(20, min(int(max_observations), 500))

    def create_job(
        self,
        request: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        created = _iso(_utc(now))
        budget = _record(request.get("budget"))
        row = {
            "job_id": new_id("research_refresh"),
            "request_id": request["request_id"],
            "symbol": request["symbol"],
            "asset_class": request["asset_class"],
            "interval": request["interval"],
            "range_name": request["range"],
            "runtime_mode": request["runtime_mode"],
            "panels_json": json_dumps(request["panels"]),
            "status": "queued",
            "progress_current": 0,
            "progress_total": len(request["panels"]),
            "planned_calls": int(budget.get("planned_calls") or 0),
            "actual_calls": 0,
            "cache_hits": 0,
            "stale_hits": 0,
            "failed_calls": 0,
            "rate_limited_calls": 0,
            "skipped_calls": 0,
            "retained_lkg": 0,
            "started_at": None,
            "completed_at": None,
            "last_attempt_at": created,
            "last_success_at": None,
            "next_retry_at": None,
            "retry_reason": "",
            "error_summary": "",
            "events_json": json_dumps(
                [{"status": "queued", "at": created, "message": "Exact refresh queued."}]
            ),
            "panel_results_json": "[]",
            "created_at": created,
            "updated_at": created,
        }
        self._write_job(row)
        self._trim_jobs()
        return self.get_job(row["job_id"]) or {}

    def update_job(
        self,
        job_id: str,
        *,
        now: datetime | None = None,
        **updates: Any,
    ) -> dict[str, Any]:
        current = self.get_job(job_id)
        if not current:
            raise KeyError(f"Unknown research refresh job: {job_id}")
        row = self._storage_row(current)
        for key, value in updates.items():
            storage_key = {
                "panels": "panels_json",
                "events": "events_json",
                "panel_results": "panel_results_json",
            }.get(key, key)
            if storage_key in {"panels_json", "events_json", "panel_results_json"}:
                row[storage_key] = json_dumps(_public(value))
            elif storage_key in row:
                row[storage_key] = value
        row["updated_at"] = _iso(_utc(now))
        self._write_job(row)
        self._trim_jobs()
        return self.get_job(job_id) or {}

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        row = execute_query(
            "SELECT * FROM research_refresh_jobs WHERE job_id = ?",
            (str(job_id),),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        return self._decode_job(row if isinstance(row, dict) else None)

    def find_active_by_request(self, request_id: str) -> dict[str, Any] | None:
        row = execute_query(
            """
            SELECT * FROM research_refresh_jobs
            WHERE request_id = ? AND status IN ('queued', 'running')
            ORDER BY created_at DESC LIMIT 1
            """,
            (request_id,),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        return self._decode_job(row if isinstance(row, dict) else None)

    def find_active_by_symbol(self, symbol: str) -> dict[str, Any] | None:
        row = execute_query(
            """
            SELECT * FROM research_refresh_jobs
            WHERE symbol = ? AND status IN ('queued', 'running')
            ORDER BY created_at DESC LIMIT 1
            """,
            (str(symbol).upper(),),
            fetch=True,
            one=True,
            db_path=self.db_path,
        )
        return self._decode_job(row if isinstance(row, dict) else None)

    def list_jobs(
        self,
        symbol: str,
        *,
        limit: int = MAX_PUBLIC_JOBS,
    ) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), MAX_PUBLIC_JOBS))
        rows = execute_query(
            """
            SELECT * FROM research_refresh_jobs
            WHERE symbol = ?
            ORDER BY created_at DESC, job_id DESC LIMIT ?
            """,
            (str(symbol).upper(), bounded),
            fetch=True,
            db_path=self.db_path,
        )
        return [
            decoded
            for row in (rows if isinstance(rows, list) else [])
            if (decoded := self._decode_job(row if isinstance(row, dict) else None))
        ]

    def record_observation(self, row: dict[str, Any]) -> dict[str, Any]:
        public = _public(row)
        values = {
            "observation_id": public["observation_id"],
            "request_id": public["request_id"],
            "symbol": public["symbol"],
            "asset_class": public["asset_class"],
            "interval": public["interval"],
            "range_name": public["range"],
            "panel": public["panel"],
            "provider": public["provider"],
            "source": public.get("source") or "",
            "source_url": _safe_url(public.get("source_url")) or "",
            "source_status": public["source_status"],
            "retrieved_at": _iso(public.get("retrieved_at")),
            "observed_at": _iso(public.get("observed_at")),
            "contacted": int(bool(public.get("contacted"))),
            "successful": int(bool(public.get("successful"))),
            "cached": int(bool(public.get("cached"))),
            "row_count": public.get("row_count"),
            "caveat": str(public.get("caveat") or "")[:1_000],
            "data_gap": str(public.get("data_gap") or "")[:1_000],
            "created_at": _iso(public.get("created_at") or _utc()),
        }
        execute_query(
            """
            INSERT OR REPLACE INTO research_panel_observations (
                observation_id, request_id, symbol, asset_class, interval,
                range_name, panel, provider, source, source_url, source_status,
                retrieved_at, observed_at, contacted, successful, cached,
                row_count, caveat, data_gap, created_at
            ) VALUES (
                :observation_id, :request_id, :symbol, :asset_class, :interval,
                :range_name, :panel, :provider, :source, :source_url,
                :source_status, :retrieved_at, :observed_at, :contacted,
                :successful, :cached, :row_count, :caveat, :data_gap,
                :created_at
            )
            """,
            values,
            db_path=self.db_path,
        )
        self._trim_observations()
        return self._decode_observation(values)

    def list_panel_observations(
        self,
        symbol: str | None = None,
        *,
        limit: int = MAX_PUBLIC_OBSERVATIONS,
    ) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), MAX_PUBLIC_OBSERVATIONS))
        if symbol:
            query = """
                SELECT * FROM research_panel_observations
                WHERE symbol = ?
                ORDER BY created_at DESC, observation_id DESC LIMIT ?
            """
            params: tuple[Any, ...] = (str(symbol).upper(), bounded)
        else:
            query = """
                SELECT * FROM research_panel_observations
                ORDER BY created_at DESC, observation_id DESC LIMIT ?
            """
            params = (bounded,)
        rows = execute_query(
            query,
            params,
            fetch=True,
            db_path=self.db_path,
        )
        return [
            self._decode_observation(row)
            for row in (rows if isinstance(rows, list) else [])
            if isinstance(row, dict)
        ]

    def _write_job(self, row: dict[str, Any]) -> None:
        execute_query(
            """
            INSERT OR REPLACE INTO research_refresh_jobs (
                job_id, request_id, symbol, asset_class, interval, range_name,
                runtime_mode, panels_json, status, progress_current,
                progress_total, planned_calls, actual_calls, cache_hits,
                stale_hits, failed_calls, rate_limited_calls, skipped_calls,
                retained_lkg, started_at, completed_at, last_attempt_at,
                last_success_at, next_retry_at, retry_reason, error_summary,
                events_json, panel_results_json, created_at, updated_at
            ) VALUES (
                :job_id, :request_id, :symbol, :asset_class, :interval,
                :range_name, :runtime_mode, :panels_json, :status,
                :progress_current, :progress_total, :planned_calls,
                :actual_calls, :cache_hits, :stale_hits, :failed_calls,
                :rate_limited_calls, :skipped_calls, :retained_lkg,
                :started_at, :completed_at, :last_attempt_at,
                :last_success_at, :next_retry_at, :retry_reason,
                :error_summary, :events_json, :panel_results_json,
                :created_at, :updated_at
            )
            """,
            row,
            db_path=self.db_path,
        )

    def _storage_row(self, job: dict[str, Any]) -> dict[str, Any]:
        row = dict(job)
        row["panels_json"] = json_dumps(row.pop("panels", []))
        row["events_json"] = json_dumps(row.pop("events", []))
        row["panel_results_json"] = json_dumps(row.pop("panel_results", []))
        row["retained_lkg"] = int(bool(row.get("retained_lkg")))
        row.pop("progress", None)
        row.pop("range", None)
        row.pop("idempotent_reuse", None)
        return row

    def _decode_job(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if not row:
            return None
        current = dict(row)
        panels = json_loads(current.pop("panels_json", "[]"), [])
        events = json_loads(current.pop("events_json", "[]"), [])
        panel_results = json_loads(
            current.pop("panel_results_json", "[]"),
            [],
        )
        current["panels"] = list(panels or [])[: len(ALLOWED_REFRESH_PANELS)]
        current["events"] = _public(list(events or [])[-MAX_JOB_EVENTS:])
        current["panel_results"] = _public(
            list(panel_results or [])[: len(ALLOWED_REFRESH_PANELS)]
        )
        current["retained_lkg"] = bool(current.get("retained_lkg"))
        current["range"] = current.get("range_name")
        total = max(0, int(current.get("progress_total") or 0))
        done = max(0, min(int(current.get("progress_current") or 0), total))
        current["progress"] = {
            "current": done,
            "total": total,
            "percent": round(done / total * 100, 1) if total else 0.0,
        }
        return _public(current)

    @staticmethod
    def _decode_observation(row: dict[str, Any]) -> dict[str, Any]:
        current = dict(row)
        current["range"] = current.pop("range_name", current.get("range"))
        current["contacted"] = bool(current.get("contacted"))
        current["successful"] = bool(current.get("successful"))
        current["cached"] = bool(current.get("cached"))
        return _public(current)

    def _trim_jobs(self) -> None:
        execute_query(
            """
            DELETE FROM research_refresh_jobs
            WHERE job_id NOT IN (
                SELECT job_id FROM research_refresh_jobs
                ORDER BY created_at DESC, job_id DESC LIMIT ?
            )
            """,
            (self.max_jobs,),
            db_path=self.db_path,
        )

    def _trim_observations(self) -> None:
        execute_query(
            """
            DELETE FROM research_panel_observations
            WHERE observation_id NOT IN (
                SELECT observation_id FROM research_panel_observations
                ORDER BY created_at DESC, observation_id DESC LIMIT ?
            )
            """,
            (self.max_observations,),
            db_path=self.db_path,
        )


def _workstation(payload: dict[str, Any]) -> dict[str, Any]:
    data = _record(payload.get("data")) or _record(payload)
    return next(iter(_records(data.get("workstations"))), {})


def _observation_clock(panel: str, workstation: dict[str, Any]) -> str | None:
    clock = _record(workstation.get("market_clock"))
    if panel in {"chart-core", "technicals", "comparison"}:
        return _iso(clock.get("market_data_as_of"))
    if panel == "news":
        rows = _records(_record(workstation.get("exact_news")).get("rows"))
        clocks = [
            _iso(row.get("published_at"))
            for row in rows
            if _iso(row.get("published_at"))
        ]
        return max(clocks, default=None)
    if panel == "catalysts":
        context = _record(workstation.get("catalyst_context"))
        event = _record(context.get("next_event"))
        return _iso(event.get("event_date"))
    if panel == "financials":
        facts = _records(
            _record(_record(workstation.get("financial_context")).get("sec_facts")).get(
                "facts"
            )
        )
        clocks = [_iso(row.get("filed")) for row in facts if _iso(row.get("filed"))]
        return max(clocks, default=None)
    return None


def record_panel_delivery_observations(
    store: ResearchOperationsStore,
    request: dict[str, Any],
    panel: str,
    payload: dict[str, Any],
    *,
    attempted_at: datetime | None = None,
) -> list[dict[str, Any]]:
    if panel not in request.get("panels", []) and panel not in ALLOWED_REFRESH_PANELS:
        raise ValueError("Unsupported panel observation.")
    workstation = _workstation(payload)
    identity = _record(workstation.get("identity"))
    if str(identity.get("symbol") or "").upper() != request["symbol"]:
        raise ValueError("Panel delivery identity does not match the exact request.")
    summary = _record(workstation.get("summary"))
    clock = _record(workstation.get("market_clock"))
    rows = _records(workstation.get("source_register"))
    if not rows:
        rows = [
            {
                "provider": summary.get("provider") or "unavailable",
                "source": f"{request['symbol']} {panel}",
                "source_url": _record(workstation.get("quote")).get("source_url"),
                "source_status": summary.get("source_status") or "unavailable",
                "fetched_at": summary.get("fetched_at")
                or clock.get("retrieved_at"),
                "row_count": summary.get("history_row_count"),
                "caveat": "No detailed source register row was returned.",
                "data_gap": "Provider-level operation evidence is incomplete.",
            }
        ]
    created = _iso(_utc(attempted_at))
    observed_at = _observation_clock(panel, workstation)
    output = []
    for index, raw in enumerate(rows[:12]):
        status = _normalize_status(raw.get("source_status"))
        provider = str(raw.get("provider") or "unavailable")[:120]
        retrieved = _iso(
            raw.get("fetched_at")
            or summary.get("fetched_at")
            or clock.get("retrieved_at")
            or attempted_at
        )
        basis = (
            f"{request['request_id']}:{panel}:{provider}:{index}:"
            f"{retrieved or created}"
        )
        observation = {
            "observation_id": "research_obs_"
            + hashlib.sha256(basis.encode()).hexdigest()[:20],
            "request_id": request["request_id"],
            "symbol": request["symbol"],
            "asset_class": request["asset_class"],
            "interval": request["interval"],
            "range": request["range"],
            "panel": panel,
            "provider": provider,
            "source": str(raw.get("source") or "")[:200],
            "source_url": _safe_url(raw.get("source_url")),
            "source_status": status,
            "retrieved_at": retrieved,
            "observed_at": observed_at,
            "contacted": status
            not in {"cached", "missing-key", "not-applicable", "not-loaded"},
            "successful": status in SUCCESS_STATUSES or status == "stale",
            "cached": status == "cached",
            "row_count": raw.get("row_count"),
            "caveat": raw.get("caveat") or "",
            "data_gap": raw.get("data_gap"),
            "created_at": created,
        }
        output.append(store.record_observation(observation))
    return output


PanelFetcher = Callable[[dict[str, Any], str], dict[str, Any]]


def _default_panel_fetcher(
    request: dict[str, Any],
    panel: str,
) -> dict[str, Any]:
    return build_symbol_delivery_contract(
        request["symbol"],
        asset_class=request["asset_class"],
        interval=request["interval"],
        range_name=request["range"],
        runtime_mode=request["runtime_mode"],
        delivery=panel,
    )


class ResearchRefreshCoordinator:
    def __init__(
        self,
        *,
        store: ResearchOperationsStore | None = None,
        panel_fetcher: PanelFetcher | None = None,
        auto_start: bool = True,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store or ResearchOperationsStore()
        self.panel_fetcher = panel_fetcher or _default_panel_fetcher
        self.auto_start = bool(auto_start)
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}

    def submit(self, request: dict[str, Any]) -> dict[str, Any]:
        exact = resolve_symbol(
            request["symbol"],
            asset_class=request["asset_class"],
        )
        if not exact or str(exact.get("symbol") or "").upper() != request["symbol"]:
            raise ValueError("Unknown exact refresh symbol.")
        with self._lock:
            same = self.store.find_active_by_request(request["request_id"])
            if same:
                return {**same, "idempotent_reuse": True}
            active = self.store.find_active_by_symbol(request["symbol"])
            if active:
                return {
                    "job_id": None,
                    "request_id": request["request_id"],
                    "symbol": request["symbol"],
                    "status": "overlap",
                    "overlap_job_id": active["job_id"],
                    "overlap_state": "same-symbol-active",
                    "idempotent_reuse": False,
                    "planned_calls": request["budget"]["planned_calls"],
                    "actual_calls": 0,
                    "retained_lkg": bool(
                        any(
                            row.get("status") == "completed"
                            for row in self.store.list_jobs(request["symbol"])
                        )
                    ),
                    "not_financial_advice": True,
                }
            job = self.store.create_job(request, now=self.now_fn())
            if self.auto_start:
                thread = threading.Thread(
                    target=self._run_guarded,
                    args=(job["job_id"],),
                    name=f"research-refresh-{request['symbol']}",
                    daemon=True,
                )
                self._threads[job["job_id"]] = thread
                thread.start()
            return {**job, "idempotent_reuse": False}

    def _run_guarded(self, job_id: str) -> None:
        try:
            self.run(job_id)
        finally:
            with self._lock:
                self._threads.pop(job_id, None)

    def run(self, job_id: str) -> dict[str, Any]:
        job = self.store.get_job(job_id)
        if not job:
            raise KeyError(f"Unknown research refresh job: {job_id}")
        if job["status"] not in ACTIVE_JOB_STATUSES:
            return job
        request = {
            "request_id": job["request_id"],
            "symbol": job["symbol"],
            "asset_class": job["asset_class"],
            "interval": job["interval"],
            "range": job["range"],
            "panels": job["panels"],
            "runtime_mode": job["runtime_mode"],
            "budget": plan_refresh_budget(
                job["panels"],
                asset_class=job["asset_class"],
            ),
        }
        now = _utc(self.now_fn())
        events = [
            *job.get("events", []),
            {
                "status": "running",
                "at": _iso(now),
                "message": "Exact refresh worker started.",
            },
        ][-MAX_JOB_EVENTS:]
        job = self.store.update_job(
            job_id,
            status="running",
            started_at=_iso(now),
            last_attempt_at=_iso(now),
            events=events,
            now=now,
        )
        prior_success = next(
            (
                row
                for row in self.store.list_jobs(job["symbol"])
                if row["job_id"] != job_id and row.get("status") == "completed"
            ),
            None,
        )
        budget = plan_refresh_budget(
            request["panels"],
            asset_class=request["asset_class"],
        )
        panel_results: list[dict[str, Any]] = []
        completed = 0
        errors: list[str] = []
        for index, panel in enumerate(request["panels"], start=1):
            planned_for_panel = int(
                budget["planned_by_panel"].get(panel) or 0
            )
            try:
                payload = self.panel_fetcher(request, panel)
                observations = record_panel_delivery_observations(
                    self.store,
                    request,
                    panel,
                    payload,
                    attempted_at=self.now_fn(),
                )
                statuses = {
                    _normalize_status(row.get("source_status"))
                    for row in observations
                }
                cache_hits = min(
                    planned_for_panel,
                    sum(status == "cached" for status in statuses),
                )
                stale_hits = min(
                    planned_for_panel,
                    sum(status == "stale" for status in statuses),
                )
                skipped = min(
                    planned_for_panel,
                    sum(
                        status
                        in {"missing-key", "not-applicable", "not-loaded"}
                        for status in statuses
                    ),
                )
                actual = min(
                    planned_for_panel,
                    sum(
                        status
                        not in {
                            "cached",
                            "missing-key",
                            "not-applicable",
                            "not-loaded",
                            "proxy/static",
                        }
                        for status in statuses
                    ),
                )
                if planned_for_panel and not statuses:
                    actual = 1
                rate_limited = min(
                    actual,
                    sum(status == "rate-limited" for status in statuses),
                )
                failed = min(
                    actual,
                    sum(status in FAILURE_STATUSES for status in statuses),
                )
                budget["actual_calls"] += actual
                budget["cache_hits"] += cache_hits
                budget["stale_hits"] += stale_hits
                budget["skipped_calls"] += skipped
                budget["rate_limited_calls"] += rate_limited
                budget["failed_calls"] += failed
                panel_status = (
                    "rate-limited"
                    if rate_limited
                    else "failed"
                    if failed and not any(row.get("successful") for row in observations)
                    else "stale"
                    if stale_hits
                    else "cached"
                    if cache_hits and not actual
                    else "completed"
                )
                if panel_status in {"completed", "cached", "stale"}:
                    completed += 1
                else:
                    errors.append(f"{panel}:{panel_status}")
                result = {
                    "panel": panel,
                    "status": panel_status,
                    "planned_calls": planned_for_panel,
                    "actual_calls": actual,
                    "cache_hits": cache_hits,
                    "stale_hits": stale_hits,
                    "failed_calls": failed,
                    "rate_limited_calls": rate_limited,
                    "skipped_calls": skipped,
                    "provider_count": len(
                        {row.get("provider") for row in observations}
                    ),
                    "retrieved_at": max(
                        (
                            str(row.get("retrieved_at") or "")
                            for row in observations
                        ),
                        default=None,
                    ),
                    "retained_lkg": panel_status
                    in {"failed", "rate-limited"}
                    and prior_success is not None,
                }
            except Exception as exc:
                actual = min(1, planned_for_panel)
                budget["actual_calls"] += actual
                budget["failed_calls"] += actual
                errors.append(f"{panel}:provider-error")
                result = {
                    "panel": panel,
                    "status": "failed",
                    "planned_calls": planned_for_panel,
                    "actual_calls": actual,
                    "cache_hits": 0,
                    "stale_hits": 0,
                    "failed_calls": actual,
                    "rate_limited_calls": 0,
                    "skipped_calls": 0,
                    "provider_count": 0,
                    "retrieved_at": _iso(self.now_fn()),
                    "retained_lkg": prior_success is not None,
                    "data_gap": f"Provider refresh failed: {type(exc).__name__}.",
                }
            panel_results.append(result)
            events.append(
                {
                    "status": result["status"],
                    "panel": panel,
                    "at": _iso(self.now_fn()),
                    "message": f"{panel} refresh {result['status']}.",
                }
            )
            job = self.store.update_job(
                job_id,
                progress_current=index,
                actual_calls=min(
                    int(budget["actual_calls"]),
                    int(budget["hard_ceiling"]),
                ),
                cache_hits=budget["cache_hits"],
                stale_hits=budget["stale_hits"],
                failed_calls=budget["failed_calls"],
                rate_limited_calls=budget["rate_limited_calls"],
                skipped_calls=budget["skipped_calls"],
                events=events[-MAX_JOB_EVENTS:],
                panel_results=panel_results,
                now=self.now_fn(),
            )
        has_rate_limit = budget["rate_limited_calls"] > 0
        has_provider_failure = budget["failed_calls"] > 0
        if has_rate_limit and completed == 0:
            terminal = "rate-limited"
        elif (has_rate_limit or has_provider_failure) and completed:
            terminal = "partial"
        elif completed == len(request["panels"]):
            terminal = "completed"
        elif completed:
            terminal = "partial"
        else:
            terminal = "failed"
        finished = _utc(self.now_fn())
        retry_delta = (
            timedelta(minutes=15)
            if terminal == "completed"
            else timedelta(minutes=1)
            if terminal == "rate-limited"
            else timedelta(minutes=5)
        )
        retry_reason = (
            "freshness-window"
            if terminal == "completed"
            else "provider-rate-limit"
            if terminal == "rate-limited"
            else "provider-recovery-window"
        )
        retained_lkg = bool(
            prior_success and terminal in {"partial", "rate-limited", "failed"}
        )
        events.append(
            {
                "status": terminal,
                "at": _iso(finished),
                "message": f"Exact refresh finished as {terminal}.",
            }
        )
        return self.store.update_job(
            job_id,
            status=terminal,
            progress_current=len(request["panels"]),
            completed_at=_iso(finished),
            last_success_at=_iso(finished)
            if terminal == "completed"
            else None,
            next_retry_at=_iso(finished + retry_delta),
            retry_reason=retry_reason,
            retained_lkg=int(retained_lkg),
            error_summary="; ".join(errors)[:1_000],
            actual_calls=min(
                int(budget["actual_calls"]),
                int(budget["hard_ceiling"]),
            ),
            cache_hits=budget["cache_hits"],
            stale_hits=budget["stale_hits"],
            failed_calls=budget["failed_calls"],
            rate_limited_calls=budget["rate_limited_calls"],
            skipped_calls=budget["skipped_calls"],
            events=events[-MAX_JOB_EVENTS:],
            panel_results=panel_results,
            now=finished,
        )


def build_research_operations_contract(
    request: dict[str, Any],
    *,
    store: ResearchOperationsStore | None = None,
    now: datetime | None = None,
    configured_providers: Iterable[str] | None = None,
) -> dict[str, Any]:
    operations_store = store or ResearchOperationsStore()
    current = _utc(now)
    jobs = operations_store.list_jobs(request["symbol"])
    observations = operations_store.list_panel_observations(request["symbol"])
    last_attempt = jobs[0] if jobs else {}
    last_success = next(
        (row for row in jobs if row.get("status") == "completed"),
        {},
    )
    panel_rows = []
    for panel in request["panels"]:
        panel_observations = [
            row for row in observations if row.get("panel") == panel
        ]
        latest = panel_observations[0] if panel_observations else {}
        latest_success = next(
            (row for row in panel_observations if row.get("successful")),
            {},
        )
        freshness = classify_panel_freshness(
            panel,
            retrieved_at=latest.get("retrieved_at"),
            observed_at=latest.get("observed_at"),
            now=current,
        )
        panel_rows.append(
            {
                "panel": panel,
                "symbol": request["symbol"],
                "asset_class": request["asset_class"],
                "interval": request["interval"],
                "range": request["range"],
                "provider": latest.get("provider") or "not-observed",
                "source_url": _safe_url(latest.get("source_url")),
                "source_status": latest.get("source_status")
                or "not-observed",
                **freshness,
                "last_attempt_at": latest.get("created_at"),
                "last_success_at": latest_success.get("retrieved_at"),
                "last_known_good": bool(latest_success),
                "caveat": latest.get("caveat")
                or "No exact panel observation has been recorded.",
                "data_gap": latest.get("data_gap")
                or (
                    "Open or refresh this exact panel to record operational evidence."
                    if not latest
                    else None
                ),
            }
        )
    provider_health = build_observed_provider_health(
        observations,
        configured_providers=(
            configured_provider_names()
            if configured_providers is None
            else configured_providers
        ),
    )
    active = next(
        (row for row in jobs if row.get("status") in ACTIVE_JOB_STATUSES),
        {},
    )
    budget = {
        **request["budget"],
        "actual_calls": int(last_attempt.get("actual_calls") or 0),
        "cache_hits": int(last_attempt.get("cache_hits") or 0),
        "stale_hits": int(last_attempt.get("stale_hits") or 0),
        "failed_calls": int(last_attempt.get("failed_calls") or 0),
        "rate_limited_calls": int(
            last_attempt.get("rate_limited_calls") or 0
        ),
        "skipped_calls": int(last_attempt.get("skipped_calls") or 0),
    }
    def job_summary(row: dict[str, Any]) -> dict[str, Any]:
        return {
            key: row.get(key)
            for key in (
                "job_id",
                "request_id",
                "symbol",
                "asset_class",
                "interval",
                "range",
                "panels",
                "status",
                "progress",
                "planned_calls",
                "actual_calls",
                "cache_hits",
                "stale_hits",
                "failed_calls",
                "rate_limited_calls",
                "skipped_calls",
                "retained_lkg",
                "started_at",
                "completed_at",
                "last_attempt_at",
                "last_success_at",
                "next_retry_at",
                "retry_reason",
                "error_summary",
            )
            if row.get(key) is not None
        }

    compact_source_register = [
        {
            key: row.get(key)
            for key in (
                "provider",
                "source_status",
                "configured",
                "contacted",
                "successful",
                "fetched_at",
                "source_url",
            )
            if row.get(key) is not None
        }
        for row in provider_health
    ]
    return _public(
        {
            "operations_version": RESEARCH_OPERATIONS_VERSION,
            "identity": {
                "symbol": request["symbol"],
                "asset_class": request["asset_class"],
                "interval": request["interval"],
                "range": request["range"],
                "panels": request["panels"],
                "request_fingerprint": request["request_fingerprint"],
                "exact": True,
            },
            "generated_at": _iso(current),
            "panels": panel_rows,
            "provider_health": provider_health,
            "budget": budget,
            "queue": {
                "status": active.get("status") or "idle",
                "active_job_id": active.get("job_id"),
                "progress": active.get("progress")
                or {"current": 0, "total": 0, "percent": 0.0},
                "overlap_state": "same-symbol-active" if active else "idle",
                "single_flight": True,
                "idempotent": True,
                "automatic_retry": False,
            },
            "last_attempt": job_summary(last_attempt),
            "last_success": job_summary(last_success),
            "last_attempt_at": last_attempt.get("last_attempt_at"),
            "last_success_at": last_success.get("last_success_at")
            or last_success.get("completed_at"),
            "last_known_good": bool(last_success),
            "next_safe_retry_at": last_attempt.get("next_retry_at"),
            "retry_reason": last_attempt.get("retry_reason") or "not-run",
            "bounded_event_history": [
                job_summary(row) for row in jobs[:MAX_OPERATIONS_HISTORY]
            ],
            "runtime_truth": {
                "process_local_worker": True,
                "installed_background_service": False,
                "hosted_scheduler": False,
                "notification_delivery": False,
                "remote_control": False,
                "kill_switch_ready": True,
                "broker_execution": False,
                "autonomous_ai_action": False,
            },
            "source_register": compact_source_register,
            "readiness": {
                "status": active.get("status")
                or last_attempt.get("status")
                or "not-run",
                "exact_identity": True,
                "observed_provider_count": len(
                    [row for row in provider_health if row.get("contacted")]
                ),
                "configured_only_count": len(
                    [
                        row
                        for row in provider_health
                        if row.get("configured") and not row.get("contacted")
                    ]
                ),
            },
            "evidence_refs": [
                "docs/PHASE_6I_RESEARCH_OPERATIONS_CONTRACT.md",
                "docs/PHASE_6I_PREFLIGHT_AND_BOTTLENECKS.md",
            ],
            "caveat": (
                "This is a bounded process-local research refresh surface. "
                "It is not an installed or hosted scheduler."
            ),
            "not_financial_advice": True,
        }
    )


_DEFAULT_STORE = ResearchOperationsStore()
_DEFAULT_COORDINATOR = ResearchRefreshCoordinator(store=_DEFAULT_STORE)


def get_default_operations_store() -> ResearchOperationsStore:
    return _DEFAULT_STORE


def submit_exact_refresh(request: dict[str, Any]) -> dict[str, Any]:
    return _DEFAULT_COORDINATOR.submit(request)


def get_research_refresh_job(job_id: str) -> dict[str, Any] | None:
    return _DEFAULT_STORE.get_job(job_id)
