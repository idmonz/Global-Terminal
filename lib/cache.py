from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from time import monotonic
from typing import Any, Callable

from .config import CACHE_DIR
from .data_status import DataResult, failure, success

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


_MEMORY_CACHE: dict[tuple[str, tuple[Any, ...], tuple[tuple[str, Any], ...]], tuple[float, Any]] = {}


def _cache_file(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def load_json_cache(key: str, ttl_seconds: int) -> tuple[Any | None, DataResult | None]:
    path = _cache_file(key)
    if not path.exists():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(payload["fetched_at"])
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        status = success(
            payload.get("data"),
            source=payload.get("source", "local cache"),
            provider=payload.get("provider", "cache"),
            stale_after_seconds=ttl_seconds,
            is_cached=True,
            coverage="stale cached data" if age > ttl_seconds else "cached data",
            warning="Cached data is stale." if age > ttl_seconds else None,
        )
        return payload.get("data"), status
    except Exception as exc:
        return None, failure(source=str(path), provider="cache", error=f"Cache read failed: {exc}")


def save_json_cache(key: str, data: Any, *, source: str, provider: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_file(key)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "provider": provider,
        "data": data,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")


def fetch_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    provider: str,
    source: str,
    ttl_seconds: int = 900,
    timeout: int = 12,
    cache_key: str | None = None,
) -> tuple[Any | None, DataResult]:
    key = cache_key or f"{provider}:{url}:{json.dumps(params or {}, sort_keys=True)}"
    cached_data, cached_status = load_json_cache(key, ttl_seconds)
    if requests is None:
        if cached_status is not None:
            return cached_data, cached_status
        return None, failure(source=source, provider=provider, error="requests is not installed")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        if response.status_code == 401:
            return cached_data, failure(source=source, provider=provider, error="401 unauthorized", is_paid_required=True)
        if response.status_code == 403:
            return cached_data, failure(source=source, provider=provider, error="403 subscription or permission required", is_paid_required=True)
        if response.status_code == 429:
            return cached_data, failure(source=source, provider=provider, error="429 rate limited", warning="Provider rate limit reached.")
        response.raise_for_status()
        data = response.json()
        save_json_cache(key, data, source=source, provider=provider)
        return data, success(data, source=source, provider=provider, stale_after_seconds=ttl_seconds)
    except Exception as exc:
        if cached_status is not None:
            cached_status.warning = f"Live fetch failed; using cache. {exc}"
            return cached_data, cached_status
        return None, failure(source=source, provider=provider, error=str(exc))


def ttl_cache(seconds: int = 300):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            now = monotonic()
            if key in _MEMORY_CACHE:
                created, value = _MEMORY_CACHE[key]
                if now - created <= seconds:
                    return value
            value = func(*args, **kwargs)
            _MEMORY_CACHE[key] = (now, value)
            return value

        return wrapper

    return decorator


def clear_memory_cache() -> None:
    _MEMORY_CACHE.clear()


def cache_status_payload() -> dict[str, Any]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    files = list(CACHE_DIR.glob("*.json"))
    return {
        "cache_dir": str(CACHE_DIR),
        "disk_entries": len(files),
        "memory_entries": len(_MEMORY_CACHE),
        "caveat": "Cache contains generated artifacts and is excluded from release packages.",
    }
