from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import CACHE_DIR
from .data_status import DataResult, failure, record_result

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


RUNTIME_CACHE_DIR = CACHE_DIR / "runtime"


@dataclass
class RuntimeCacheRecord:
    key: str
    data: Any
    source: str
    provider: str
    source_url: str
    fetched_at: datetime

    @property
    def fetched_at_iso(self) -> str:
        return self.fetched_at.isoformat()

    def age_seconds(self, now: datetime | None = None) -> float:
        current = now or datetime.now(timezone.utc)
        return max(0.0, (current - self.fetched_at).total_seconds())

    def is_fresh(self, ttl_seconds: int, now: datetime | None = None) -> bool:
        return self.age_seconds(now) <= ttl_seconds

    def to_payload(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "data": self.data,
            "source": self.source,
            "provider": self.provider,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at_iso,
        }


_MEMORY_CACHE: dict[str, RuntimeCacheRecord] = {}
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return RUNTIME_CACHE_DIR / f"{digest}.json"


def _lock_for(key: str) -> threading.Lock:
    with _LOCKS_GUARD:
        if key not in _LOCKS:
            _LOCKS[key] = threading.Lock()
        return _LOCKS[key]


def _parse_datetime(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _record_to_status(
    record: RuntimeCacheRecord,
    *,
    ttl_seconds: int,
    warning: str | None = None,
    coverage: str = "cached data",
) -> DataResult:
    return record_result(
        DataResult(
            ok=True,
            data=record.data,
            source=record.source,
            provider=record.provider,
            fetched_at=record.fetched_at,
            stale_after_seconds=ttl_seconds,
            warning=warning,
            is_cached=True,
            is_estimated=False,
            coverage=coverage,
        )
    )


def _fresh_status(
    data: Any,
    *,
    source: str,
    provider: str,
    ttl_seconds: int,
    coverage: str = "live data",
) -> DataResult:
    return record_result(
        DataResult(
            ok=True,
            data=data,
            source=source,
            provider=provider,
            fetched_at=datetime.now(timezone.utc),
            stale_after_seconds=ttl_seconds,
            is_cached=False,
            coverage=coverage,
        )
    )


def load_runtime_cache_record(key: str) -> RuntimeCacheRecord | None:
    if key in _MEMORY_CACHE:
        return _MEMORY_CACHE[key]
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = RuntimeCacheRecord(
            key=str(payload.get("key") or key),
            data=payload.get("data"),
            source=str(payload.get("source") or "runtime cache"),
            provider=str(payload.get("provider") or "runtime_cache"),
            source_url=str(payload.get("source_url") or ""),
            fetched_at=_parse_datetime(payload.get("fetched_at")),
        )
        _MEMORY_CACHE[key] = record
        return record
    except Exception:
        return None


def save_runtime_cache_record(record: RuntimeCacheRecord) -> None:
    RUNTIME_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _MEMORY_CACHE[record.key] = record
    _cache_path(record.key).write_text(json.dumps(record.to_payload(), ensure_ascii=False, default=str), encoding="utf-8")


def clear_runtime_cache() -> None:
    _MEMORY_CACHE.clear()


def fetch_json_with_cache(
    key: str,
    url: str,
    *,
    provider: str,
    source: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    ttl_seconds: int = 900,
    timeout: int = 10,
    session: Any | None = None,
) -> tuple[Any | None, DataResult]:
    """Fetch JSON with TTL cache, stale fallback, timeouts, and per-key single-flight."""
    with _lock_for(key):
        cached = load_runtime_cache_record(key)
        if cached is not None and cached.is_fresh(ttl_seconds):
            return cached.data, _record_to_status(cached, ttl_seconds=ttl_seconds, coverage="fresh cached data")
        if requests is None and session is None:
            if cached is not None:
                return cached.data, _record_to_status(
                    cached,
                    ttl_seconds=ttl_seconds,
                    warning="requests is unavailable; using cached runtime data.",
                    coverage="stale cached data",
                )
            return None, failure(source=source, provider=provider, error="requests is not installed")
        client = session or requests
        try:
            response = client.get(url, params=params, headers=headers, timeout=timeout)
            status_code = getattr(response, "status_code", None)
            if status_code == 401:
                raise PermissionError("401 unauthorized")
            if status_code == 403:
                raise PermissionError("403 forbidden or subscription required")
            if status_code == 429:
                raise RuntimeError("429 rate limited")
            response.raise_for_status()
            data = response.json()
            record = RuntimeCacheRecord(
                key=key,
                data=data,
                source=source,
                provider=provider,
                source_url=url,
                fetched_at=datetime.now(timezone.utc),
            )
            save_runtime_cache_record(record)
            return data, _fresh_status(data, source=source, provider=provider, ttl_seconds=ttl_seconds)
        except Exception as exc:
            if cached is not None:
                return cached.data, _record_to_status(
                    cached,
                    ttl_seconds=ttl_seconds,
                    warning=f"Live fetch failed; using stale cache. {exc}",
                    coverage="stale cached data",
                )
            return None, failure(source=source, provider=provider, error=str(exc), warning="No cached fallback is available.")


def fetch_text_with_cache(
    key: str,
    url: str,
    *,
    provider: str,
    source: str,
    headers: dict[str, str] | None = None,
    ttl_seconds: int = 900,
    timeout: int = 10,
    session: Any | None = None,
) -> tuple[str | None, DataResult]:
    """Fetch text with the same TTL, stale fallback, and single-flight boundary as JSON."""
    with _lock_for(key):
        cached = load_runtime_cache_record(key)
        if cached is not None and cached.is_fresh(ttl_seconds) and isinstance(cached.data, str):
            return cached.data, _record_to_status(cached, ttl_seconds=ttl_seconds, coverage="fresh cached text")
        if requests is None and session is None:
            if cached is not None and isinstance(cached.data, str):
                return cached.data, _record_to_status(
                    cached,
                    ttl_seconds=ttl_seconds,
                    warning="requests is unavailable; using cached runtime text.",
                    coverage="stale cached text",
                )
            return None, failure(source=source, provider=provider, error="requests is not installed")
        client = session or requests
        try:
            response = client.get(url, headers=headers, timeout=timeout)
            status_code = getattr(response, "status_code", None)
            if status_code == 401:
                raise PermissionError("401 unauthorized")
            if status_code == 403:
                raise PermissionError("403 forbidden or subscription required")
            if status_code == 429:
                raise RuntimeError("429 rate limited")
            response.raise_for_status()
            data = str(response.text)
            record = RuntimeCacheRecord(
                key=key,
                data=data,
                source=source,
                provider=provider,
                source_url=url,
                fetched_at=datetime.now(timezone.utc),
            )
            save_runtime_cache_record(record)
            return data, _fresh_status(data, source=source, provider=provider, ttl_seconds=ttl_seconds, coverage="live text")
        except Exception as exc:
            if cached is not None and isinstance(cached.data, str):
                return cached.data, _record_to_status(
                    cached,
                    ttl_seconds=ttl_seconds,
                    warning=f"Live fetch failed; using stale cached text. {exc}",
                    coverage="stale cached text",
                )
            return None, failure(source=source, provider=provider, error=str(exc), warning="No cached fallback is available.")
