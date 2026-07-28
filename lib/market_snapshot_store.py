from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


MARKET_SNAPSHOT_VERSION = "market_snapshot.v2"
MARKET_REFRESH_HEALTH_VERSION = "market_refresh_health.v1"
MARKET_REFRESH_HISTORY_VERSION = "market_refresh_history.v1"
DEFAULT_MAX_AGE_SECONDS = 900
DEFAULT_RETENTION = 5
_SNAPSHOT_NAME = re.compile(r"^market_snapshot_\d{8}T\d{6}Z_[a-f0-9]{16}\.json$")
_PRIVATE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "cookie",
    "db_path",
    "local_path",
    "password",
    "private_body",
    "refresh_token",
    "token",
}
_SECRET_PATTERNS = (
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsk-[0-9A-Za-z_-]{16,}\b"),
    re.compile(r"\bBearer\s+[0-9A-Za-z._-]{12,}\b", re.IGNORECASE),
)
_KEEP_DATA_FIELDS = (
    "market_map_screener_version",
    "discovery_version",
    "workspace",
    "instruments",
    "factor_catalog",
    "rank_models",
    "universe_contract",
    "saved_screen_readiness",
    "filter_options",
    "source_register",
    "unavailable_sources",
    "readiness",
    "summary",
    "caveat",
)
_COMPACT_INSTRUMENT_FIELDS = (
    "symbol",
    "name",
    "asset_class",
    "sector",
    "industry",
    "region",
    "country",
    "exchange",
    "mic",
    "market_cap",
    "size_value",
    "size_metric",
    "price",
    "return_1d_pct",
    "return_1m_pct",
    "realized_volatility_pct",
    "drawdown_pct",
    "rsi",
    "volume",
    "relative_volume",
    "market_data_as_of",
    "fetched_at",
    "provider",
    "source_url",
    "freshness",
    "source_status",
    "history_source_status",
    "confidence",
    "taxonomy_source_status",
    "workstation_supported",
    "caveat",
    "data_gap",
    "not_financial_advice",
)
_PROCESS_LOCK = threading.Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime:
    current = value or _utc_now()
    return (current if current.tzinfo else current.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _as_utc(value).replace(microsecond=0).isoformat()


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _base_dir(base_dir: str | Path | None = None) -> Path:
    configured = base_dir or os.getenv("MARKET_SNAPSHOT_DIR") or Path("data") / "cache" / "market_snapshots"
    return Path(configured).expanduser().resolve()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _content_hash(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _bounded_json(value: Any, *, depth: int = 0) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if depth > 12:
        raise ValueError("Market snapshot exceeds the supported nesting depth.")
    if isinstance(value, dict):
        return {str(key): _bounded_json(item, depth=depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_bounded_json(item, depth=depth + 1) for item in value]
    raise ValueError(f"Market snapshot contains a non-JSON value: {type(value).__name__}.")


def _assert_public(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in _PRIVATE_KEYS or normalized.endswith("_secret"):
                raise ValueError(f"Market snapshot contains a private field at {path}.")
            _assert_public(item, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_public(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and any(pattern.search(value) for pattern in _SECRET_PATTERNS):
        raise ValueError(f"Market snapshot contains a private value at {path}.")


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        temp.write_bytes(_json_bytes(value))
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def compact_market_map_payload(payload: dict[str, Any]) -> dict[str, Any]:
    safe = _bounded_json(payload)
    _assert_public(safe)
    data = safe.get("data") if isinstance(safe.get("data"), dict) else {}
    compact_data = {field: data[field] for field in _KEEP_DATA_FIELDS if field in data}
    compact_data["instruments"] = [
        _compact_instrument(row)
        for row in data.get("instruments") or []
        if isinstance(row, dict)
    ]
    compact_data["materialization"] = {
        "snapshot_version": MARKET_SNAPSHOT_VERSION,
        "read_status": "unmaterialized",
        "content_hash": None,
        "created_at": None,
        "age_seconds": None,
        "etag": None,
        "provider_refresh_on_read": False,
    }
    summary = safe.get("summary") if isinstance(safe.get("summary"), dict) else {}
    return {
        **safe,
        "data": compact_data,
        "summary": {
            **summary,
            "instrument_count": len(compact_data.get("instruments") or []),
            "materialized": True,
            "compact_first_paint": True,
        },
    }


def _compact_instrument(row: dict[str, Any]) -> dict[str, Any]:
    compact = {field: row.get(field) for field in _COMPACT_INSTRUMENT_FIELDS if field in row}
    compact["membership"] = {
        field: (row.get("membership") or {}).get(field)
        for field in ("provider", "source_status", "as_of", "listing_status", "exchange", "mic", "security_type", "cik", "sec_source_status")
    }
    compact["taxonomy"] = {
        field: (row.get("taxonomy") or {}).get(field)
        for field in (
            "provider",
            "source_status",
            "classification_version",
            "reviewed_at",
            "sector",
            "industry",
            "provider_sector",
            "taxonomy_authoritative",
            "classification_conflict",
        )
    }
    compact["data_quality"] = {
        field: (row.get("data_quality") or {}).get(field)
        for field in ("score", "status")
    }
    compact["factors"] = {
        field: (row.get("factors") or {}).get(field)
        for field in (
            "trend_state",
            "valuation_available",
            "trailing_pe",
            "forward_pe",
            "price_to_book",
        )
    }
    compact["financial_snapshot"] = {
        field: (row.get("financial_snapshot") or {}).get(field)
        for field in ("provider", "source_status")
    }
    compact["market_clock"] = {
        field: (row.get("market_clock") or {}).get(field)
        for field in ("market_data_as_of", "retrieved_at", "exchange_delay_minutes")
    }
    compact["rank_models"] = {
        model_id: {
            "eligible": model.get("eligible"),
            "score": model.get("score"),
            "rank": model.get("rank"),
            "contributions": [
                {
                    "factor_id": item.get("factor_id"),
                    "contribution": item.get("contribution"),
                }
                for item in model.get("contributions") or []
                if isinstance(item, dict)
            ],
            "exclusion_reasons": list(model.get("exclusion_reasons") or []),
        }
        for model_id, model in (row.get("rank_models") or {}).items()
        if isinstance(model, dict) and model.get("eligible") is True
    }
    return compact


def materialize_market_snapshot(
    payload: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
    now: datetime | None = None,
    retention: int = DEFAULT_RETENTION,
) -> dict[str, Any]:
    keep = max(1, min(int(retention), 50))
    created = _as_utc(now)
    safe_payload = _bounded_json(payload)
    _assert_public(safe_payload)
    safe_data = safe_payload.get("data") if isinstance(safe_payload.get("data"), dict) else {}
    details = {
        str(row.get("symbol") or "").upper(): row
        for row in safe_data.get("instruments") or []
        if isinstance(row, dict) and row.get("symbol")
    }
    compact = compact_market_map_payload(payload)
    detail_hash = _content_hash(details)
    digest_basis = {
        "snapshot_version": MARKET_SNAPSHOT_VERSION,
        "created_at": _iso(created),
        "envelope": compact,
        "detail_hash": detail_hash,
    }
    digest = _content_hash(digest_basis)
    read_etag = _content_hash({"content_hash": digest, "read_status": "fresh"})
    compact["data"]["materialization"].update(
        {
            "read_status": "fresh",
            "content_hash": digest,
            "created_at": _iso(created),
            "age_seconds": 0,
            "etag": read_etag,
        }
    )
    stored = {
        "snapshot_version": MARKET_SNAPSHOT_VERSION,
        "content_hash": digest,
        "created_at": _iso(created),
        "instrument_count": len(compact["data"].get("instruments") or []),
        "payload_bytes": len(_json_bytes(compact)),
        "envelope": compact,
        "detail_hash": detail_hash,
        "details": details,
    }
    _assert_public(stored)
    root = _base_dir(base_dir)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    snapshot_name = f"market_snapshot_{stamp}_{digest[:16]}.json"
    snapshot_path = root / snapshot_name
    _atomic_write_json(snapshot_path, stored)
    _atomic_write_json(
        root / "latest.json",
        {
            "snapshot_version": MARKET_SNAPSHOT_VERSION,
            "snapshot_file": snapshot_name,
            "content_hash": digest,
            "created_at": _iso(created),
        },
    )
    _prune_snapshots(root, keep=keep, preserve=snapshot_name)
    return {
        "snapshot_version": MARKET_SNAPSHOT_VERSION,
        "snapshot_path": snapshot_path.as_posix(),
        "snapshot_file": snapshot_name,
        "content_hash": digest,
        "created_at": _iso(created),
        "instrument_count": stored["instrument_count"],
        "payload_bytes": stored["payload_bytes"],
        "provider_call_count": _observed_provider_call_count(compact),
        "provider_source_count": _provider_source_count(compact),
        "taxonomy_coverage_count": int((compact["data"].get("universe_contract") or {}).get("taxonomy_coverage_count") or 0),
        "industry_coverage_count": int((compact["data"].get("universe_contract") or {}).get("industry_coverage_count") or 0),
        "unclassified_count": int((compact["data"].get("universe_contract") or {}).get("unclassified_count") or 0),
        "excluded_observation_count": int((compact["data"].get("universe_contract") or {}).get("excluded_unverified_observation_count") or 0),
    }


def _prune_snapshots(root: Path, *, keep: int, preserve: str) -> None:
    candidates = sorted(
        (path for path in root.glob("market_snapshot_*.json") if _SNAPSHOT_NAME.fullmatch(path.name)),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    retained = {path.name for path in candidates[:keep]}
    retained.add(preserve)
    for path in candidates:
        if path.name not in retained:
            path.unlink()


def _unavailable_payload(status: str, message: str) -> dict[str, Any]:
    return {
        "contract_version": "phase_2b.v1",
        "payload_type": "market_map_screener",
        "generated_at": _iso(_utc_now()),
        "data": {
            "instruments": [],
            "materialization": {
                "snapshot_version": MARKET_SNAPSHOT_VERSION,
                "read_status": status,
                "content_hash": None,
                "created_at": None,
                "age_seconds": None,
                "etag": None,
                "provider_refresh_on_read": False,
            },
        },
        "summary": {
            "instrument_count": 0,
            "source_status": "unavailable",
            "materialized": True,
            "compact_first_paint": True,
        },
        "source_status": [],
        "unavailable": [
            {
                "provider": "market_snapshot_store",
                "source_status": "unavailable",
                "error": status,
                "data_gap": message,
                "not_financial_advice": True,
            }
        ],
        "errors": [],
        "caveats": [message],
    }


def read_market_snapshot(
    *,
    base_dir: str | Path | None = None,
    now: datetime | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    root = _base_dir(base_dir)
    manifest = _read_json(root / "latest.json")
    if not manifest:
        return _unavailable_payload("snapshot-missing", "No materialized market snapshot is available.")
    snapshot_name = str(manifest.get("snapshot_file") or "")
    if not _SNAPSHOT_NAME.fullmatch(snapshot_name):
        return _unavailable_payload("manifest-invalid", "The materialized market snapshot manifest is invalid.")
    stored = _read_json(root / snapshot_name)
    if not stored:
        return _unavailable_payload("snapshot-unreadable", "The materialized market snapshot cannot be read.")
    if stored.get("snapshot_version") != MARKET_SNAPSHOT_VERSION:
        return _unavailable_payload("schema-mismatch", "The materialized market snapshot version is unsupported.")
    envelope = stored.get("envelope")
    if not isinstance(envelope, dict):
        return _unavailable_payload("snapshot-invalid", "The materialized market snapshot payload is invalid.")
    expected = str(stored.get("content_hash") or "")
    if not expected or expected != str(manifest.get("content_hash") or ""):
        return _unavailable_payload("integrity-mismatch", "The materialized market snapshot integrity metadata does not match.")
    created = _parse_time(stored.get("created_at"))
    age = max(0.0, (_as_utc(now) - created).total_seconds()) if created else None
    read_status = "fresh" if age is not None and age <= max(0, int(max_age_seconds)) else "stale"
    output = _bounded_json(envelope)
    materialization = output.setdefault("data", {}).setdefault("materialization", {})
    refresh_health = get_market_refresh_health(base_dir=root)
    refresh_history = get_market_refresh_history(base_dir=root, limit=5)
    materialization.update(
        {
            "snapshot_version": MARKET_SNAPSHOT_VERSION,
            "read_status": read_status,
            "content_hash": expected,
            "created_at": stored.get("created_at"),
            "age_seconds": round(age, 3) if age is not None else None,
            "etag": _content_hash({"content_hash": expected, "read_status": read_status}),
            "provider_refresh_on_read": False,
            "refresh_health": {
                "status": refresh_health.get("status"),
                "last_success_at": refresh_health.get("last_success_at"),
                "duration_ms": refresh_health.get("duration_ms"),
                "instrument_count": refresh_health.get("instrument_count"),
                "payload_bytes": refresh_health.get("payload_bytes"),
                "provider_call_count": refresh_health.get("provider_call_count"),
                "provider_source_count": refresh_health.get("provider_source_count"),
            },
            "refresh_history": refresh_history.get("rows") or [],
        }
    )
    output.setdefault("summary", {}).update(
        {
            "materialized": True,
            "compact_first_paint": True,
            "snapshot_status": read_status,
            "snapshot_created_at": stored.get("created_at"),
        }
    )
    if read_status == "stale":
        output["caveats"] = [
            *list(output.get("caveats") or []),
            "The last-known-good market snapshot is stale; no provider refresh occurred on this read.",
        ]
    return output


def build_market_snapshot_detail(
    symbol: str,
    *,
    base_dir: str | Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    normalized = str(symbol or "").strip().upper()[:32]
    root = _base_dir(base_dir)
    snapshot = read_market_snapshot(base_dir=root, now=now)
    instruments = snapshot.get("data", {}).get("instruments") if isinstance(snapshot.get("data"), dict) else []
    rows = [row for row in instruments or [] if isinstance(row, dict)]
    compact_instrument = next((row for row in rows if str(row.get("symbol") or "").upper() == normalized), None)
    manifest = _read_json(root / "latest.json") or {}
    snapshot_name = str(manifest.get("snapshot_file") or "")
    stored = _read_json(root / snapshot_name) if _SNAPSHOT_NAME.fullmatch(snapshot_name) else None
    details = stored.get("details") if isinstance(stored, dict) and isinstance(stored.get("details"), dict) else {}
    instrument = details.get(normalized) if isinstance(details.get(normalized), dict) else compact_instrument
    materialization = dict(snapshot.get("data", {}).get("materialization") or {})
    status = "available" if instrument else "unknown-symbol"
    return {
        "contract_version": "phase_2b.v1",
        "payload_type": "market_snapshot_detail",
        "generated_at": _iso(_utc_now()),
        "data": {
            "instrument": instrument,
            "materialization": materialization,
        },
        "summary": {
            "symbol": normalized,
            "status": status,
            "source_status": str((instrument or {}).get("source_status") or "unavailable"),
            "materialized": True,
        },
        "source_status": list(snapshot.get("source_status") or []) if instrument else [],
        "unavailable": [] if instrument else [
            {
                "provider": "market_snapshot_store",
                "source_status": "unavailable",
                "error": "unknown-symbol",
                "data_gap": "The selected symbol is not present in the materialized market snapshot.",
                "not_financial_advice": True,
            }
        ],
        "errors": [],
        "caveats": [
            "Detail is read from the materialized Market Map snapshot; no provider request occurs on this read."
        ],
    }


def get_market_refresh_health(*, base_dir: str | Path | None = None) -> dict[str, Any]:
    health = _read_json(_base_dir(base_dir) / "refresh_health.json")
    if health and health.get("health_version") == MARKET_REFRESH_HEALTH_VERSION:
        return health
    return {
        "health_version": MARKET_REFRESH_HEALTH_VERSION,
        "status": "never-run",
        "job_id": None,
        "started_at": None,
        "finished_at": None,
        "duration_ms": None,
        "last_success_at": None,
        "last_error": None,
        "instrument_count": 0,
        "payload_bytes": 0,
        "provider_call_count": None,
        "provider_source_count": 0,
        "snapshot_version": MARKET_SNAPSHOT_VERSION,
    }


def _write_refresh_health(root: Path, health: dict[str, Any]) -> None:
    _assert_public(health)
    _atomic_write_json(root / "refresh_health.json", health)


def get_market_refresh_history(
    *,
    base_dir: str | Path | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    bounded_limit = max(1, min(int(limit), 100))
    stored = _read_json(_base_dir(base_dir) / "refresh_history.json") or {}
    rows = stored.get("rows") if stored.get("history_version") == MARKET_REFRESH_HISTORY_VERSION else []
    safe_rows = [row for row in rows or [] if isinstance(row, dict)]
    return {
        "history_version": MARKET_REFRESH_HISTORY_VERSION,
        "rows": safe_rows[:bounded_limit],
        "row_count": min(len(safe_rows), bounded_limit),
        "retained_count": len(safe_rows),
        "retention_limit": int(stored.get("retention_limit") or 100),
        "scope": "local-operational",
        "caveat": "Local refresh history is bounded operational evidence, not hosted monitoring.",
    }


def _append_refresh_history(root: Path, health: dict[str, Any], *, retention: int) -> None:
    keep = max(1, min(int(retention), 500))
    previous = get_market_refresh_history(base_dir=root, limit=100)
    allowed = (
        "job_id",
        "status",
        "started_at",
        "finished_at",
        "duration_ms",
        "last_success_at",
        "last_error",
        "instrument_count",
        "payload_bytes",
        "provider_call_count",
        "provider_source_count",
        "taxonomy_coverage_count",
        "industry_coverage_count",
        "unclassified_count",
        "excluded_observation_count",
        "snapshot_version",
        "content_hash",
    )
    row = {field: health.get(field) for field in allowed}
    rows = [row, *previous.get("rows", [])]
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()
    for item in rows:
        identity = (item.get("job_id"), item.get("status"), item.get("started_at"))
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(item)
    payload = {
        "history_version": MARKET_REFRESH_HISTORY_VERSION,
        "rows": deduped[:keep],
        "retention_limit": keep,
        "updated_at": health.get("finished_at") or health.get("started_at"),
    }
    _assert_public(payload)
    _atomic_write_json(root / "refresh_history.json", payload)


def refresh_market_snapshot(
    *,
    builder: Callable[[], dict[str, Any]],
    base_dir: str | Path | None = None,
    now: datetime | None = None,
    retention: int = DEFAULT_RETENTION,
    history_retention: int = 100,
) -> dict[str, Any]:
    root = _base_dir(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    started = _as_utc(now)
    started_clock = time.perf_counter()
    job_id = f"marketrefresh_{started.strftime('%Y%m%dT%H%M%SZ')}_{os.getpid()}"
    previous = get_market_refresh_health(base_dir=root)
    with _PROCESS_LOCK:
        lock_path = root / ".refresh.lock"
        lock_fd: int | None = None
        try:
            try:
                lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(lock_fd, job_id.encode("ascii", errors="ignore"))
            except FileExistsError:
                busy = {
                    **previous,
                    "status": "single-flight-busy",
                    "job_id": job_id,
                    "started_at": _iso(started),
                    "finished_at": _iso(_as_utc(now) if now is not None else _utc_now()),
                    "last_error": "another refresh is active",
                }
                _append_refresh_history(root, busy, retention=history_retention)
                return busy
            payload = builder()
            written = materialize_market_snapshot(payload, base_dir=root, now=started, retention=retention)
            finished = _as_utc(now) if now is not None else _utc_now()
            health = {
                "health_version": MARKET_REFRESH_HEALTH_VERSION,
                "status": "succeeded",
                "job_id": job_id,
                "started_at": _iso(started),
                "finished_at": _iso(finished),
                "duration_ms": round((time.perf_counter() - started_clock) * 1000, 3),
                "last_success_at": _iso(finished),
                "last_error": None,
                "instrument_count": written["instrument_count"],
                "payload_bytes": written["payload_bytes"],
                "provider_call_count": written["provider_call_count"],
                "provider_source_count": written["provider_source_count"],
                "taxonomy_coverage_count": written["taxonomy_coverage_count"],
                "industry_coverage_count": written["industry_coverage_count"],
                "unclassified_count": written["unclassified_count"],
                "excluded_observation_count": written["excluded_observation_count"],
                "snapshot_version": MARKET_SNAPSHOT_VERSION,
                "content_hash": written["content_hash"],
                "snapshot_file": written["snapshot_file"],
            }
            _write_refresh_health(root, health)
            _append_refresh_history(root, health, retention=history_retention)
            return health
        except Exception:
            finished = _as_utc(now) if now is not None else _utc_now()
            health = {
                **previous,
                "health_version": MARKET_REFRESH_HEALTH_VERSION,
                "status": "failed",
                "job_id": job_id,
                "started_at": _iso(started),
                "finished_at": _iso(finished),
                "duration_ms": round((time.perf_counter() - started_clock) * 1000, 3),
                "last_error": "provider refresh failed",
                "snapshot_version": MARKET_SNAPSHOT_VERSION,
            }
            _write_refresh_health(root, health)
            _append_refresh_history(root, health, retention=history_retention)
            return health
        finally:
            if lock_fd is not None:
                os.close(lock_fd)
                try:
                    lock_path.unlink()
                except OSError:
                    pass


def _source_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    rows = data.get("source_register")
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _observed_provider_call_count(payload: dict[str, Any]) -> int:
    return sum(
        int(row.get("provider_call_count"))
        if isinstance(row.get("provider_call_count"), int)
        else int(
            row.get("cached") is False
            and str(row.get("source_status") or "") == "live/fresh"
            and not str(row.get("provider") or "").startswith("phase")
        )
        for row in _source_rows(payload)
    )


def _provider_source_count(payload: dict[str, Any]) -> int:
    return sum(
        not str(row.get("provider") or "").startswith("phase")
        for row in _source_rows(payload)
    )
