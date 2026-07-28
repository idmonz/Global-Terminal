from __future__ import annotations

from uuid import uuid4

from lib.runtime_cache import clear_runtime_cache, fetch_json_with_cache


class _Response:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Session:
    def __init__(self, payload=None, error: Exception | None = None):
        self.payload = payload or {"ok": True}
        self.error = error
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return _Response(self.payload)


def test_runtime_cache_reuses_fresh_entry_without_refetch():
    clear_runtime_cache()
    key = f"unit:fresh:{uuid4()}"
    first = _Session({"rows": [1]})
    data, status = fetch_json_with_cache(key, "https://example.test/feed", provider="unit", source="unit", session=first, ttl_seconds=600)

    second = _Session(error=RuntimeError("network should not be called"))
    cached, cached_status = fetch_json_with_cache(key, "https://example.test/feed", provider="unit", source="unit", session=second, ttl_seconds=600)

    assert data == {"rows": [1]}
    assert status.ok
    assert cached == {"rows": [1]}
    assert cached_status.ok
    assert cached_status.is_cached
    assert second.calls == 0


def test_runtime_cache_returns_stale_fallback_on_fetch_failure():
    clear_runtime_cache()
    key = f"unit:stale:{uuid4()}"
    first = _Session({"rows": [2]})
    fetch_json_with_cache(key, "https://example.test/feed", provider="unit", source="unit", session=first, ttl_seconds=600)

    failing = _Session(error=TimeoutError("timeout"))
    cached, status = fetch_json_with_cache(key, "https://example.test/feed", provider="unit", source="unit", session=failing, ttl_seconds=0)

    assert cached == {"rows": [2]}
    assert status.ok
    assert status.is_cached
    assert "using stale cache" in (status.warning or "")
