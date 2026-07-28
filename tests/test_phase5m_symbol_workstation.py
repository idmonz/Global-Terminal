from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import lib.symbol_workstation as symbol_module
from backend.api import app as backend_app
from lib.api_contracts import (
    build_api_symbol_directory_payload,
    build_api_symbol_workstation_payload,
    validate_api_payload,
)
from lib.runtime_cache import RuntimeCacheRecord
from lib.symbol_workstation import (
    build_symbol_directory_contract,
    build_symbol_workstation_contract,
    history_cache_key,
    resolve_symbol,
    search_symbols,
)


ROOT = Path(__file__).resolve().parents[1]


def test_bounded_symbol_directory_meets_equity_etf_and_crypto_coverage():
    contract = build_symbol_directory_contract()
    identities = contract["identities"]
    counts = contract["asset_class_counts"]

    assert counts["equity"] + counts["etf"] >= 50
    assert counts["crypto"] >= 20
    assert len({row["symbol"] for row in identities}) == len(identities)
    assert all(row["registry_provider"] and row["source_status"] for row in identities)
    assert all(row["source_status"] == "static/proxy" for row in identities)
    assert contract["readiness"]["authoritative_security_master_claimed"] is False


def test_exact_resolver_and_search_are_stable_bounded_and_alias_aware():
    assert resolve_symbol("msft")["symbol"] == "MSFT"
    assert resolve_symbol("brk.b")["symbol"] == "BRK-B"
    assert resolve_symbol("btc/usdt")["symbol"] == "BTCUSDT"
    assert resolve_symbol("ETH-USD")["symbol"] == "ETHUSDT"
    assert resolve_symbol("SPY", asset_class="equity") is None

    results = search_symbols("micro", limit=5)
    assert results[0]["symbol"] == "MSFT"
    assert len(search_symbols("a", limit=10_000)) <= 20
    assert search_symbols("'; rm -rf /", limit=5) == []


def test_fixture_workstations_are_symbol_specific_and_do_not_leak_aapl_or_btc_rows():
    msft = build_symbol_workstation_contract(
        "MSFT",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        runtime_mode="fixture",
    )
    spy = build_symbol_workstation_contract(
        "SPY",
        asset_class="etf",
        interval="1d",
        range_name="3mo",
        runtime_mode="fixture",
    )
    eth = build_symbol_workstation_contract(
        "ETHUSDT",
        asset_class="crypto",
        interval="1d",
        range_name="3mo",
        runtime_mode="fixture",
    )

    msft_text = json.dumps(msft, sort_keys=True)
    eth_text = json.dumps(eth, sort_keys=True)
    assert msft["workstations"][0]["identity"]["name"] == "Microsoft"
    assert msft["workstations"][0]["history"]
    assert all(row["symbol"] == "MSFT" for row in msft["workstations"][0]["history"])
    assert "Apple Inc. fixture profile" not in msft_text
    assert '"symbol": "AAPL"' not in msft_text
    assert spy["workstations"][0]["identity"]["asset_class"] == "etf"
    assert eth["workstations"][0]["identity"]["name"] == "Ethereum"
    assert all(row["symbol"] == "ETHUSDT" for row in eth["workstations"][0]["history"])
    assert '"symbol": "BTCUSDT"' not in eth_text


def test_unknown_and_unsupported_capabilities_never_call_provider(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(symbol_module, "_fetch_provider_history", lambda *args, **kwargs: calls.append(args))

    unknown = build_symbol_workstation_contract(
        "NOTREAL",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        runtime_mode="live-if-available",
    )
    unsupported = build_symbol_workstation_contract(
        "MSFT",
        asset_class="equity",
        interval="15m",
        range_name="1y",
        runtime_mode="live-if-available",
    )

    assert unknown["workstations"] == []
    assert unknown["summary"]["status"] == "unknown-symbol"
    assert unsupported["workstations"][0]["history"] == []
    assert unsupported["workstations"][0]["summary"]["status"] == "unsupported-interval"
    assert calls == []


def test_history_cache_key_is_partitioned_by_symbol_interval_and_range():
    assert history_cache_key("equity", "MSFT", "1d", "3mo") != history_cache_key("equity", "AAPL", "1d", "3mo")
    assert history_cache_key("equity", "MSFT", "1d", "3mo") != history_cache_key("equity", "MSFT", "1h", "3mo")
    assert history_cache_key("equity", "MSFT", "1d", "3mo") != history_cache_key("equity", "MSFT", "1d", "1y")


def test_live_history_caches_and_provider_failure_retains_original_stale_time(monkeypatch):
    saved: dict[str, RuntimeCacheRecord] = {}
    fetched_at = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    now = fetched_at + timedelta(hours=2)
    rows = [
        {
            "date": "2026-06-20T00:00:00+00:00",
            "open": 100.0,
            "high": 103.0,
            "low": 99.0,
            "close": 102.0,
            "volume": 1000.0,
        }
    ]

    monkeypatch.setattr(symbol_module, "_utc_now", lambda: fetched_at)
    monkeypatch.setattr(symbol_module, "_load_history_cache", lambda key: saved.get(key))
    monkeypatch.setattr(symbol_module, "_save_history_cache", lambda record: saved.__setitem__(record.key, record))
    monkeypatch.setattr(symbol_module, "_fetch_provider_history", lambda *args, **kwargs: (rows, {"provider": "unit", "source_url": "https://example.test/MSFT", "fetched_at": fetched_at.isoformat()}))

    live = build_symbol_workstation_contract(
        "MSFT",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        runtime_mode="live-if-available",
    )
    assert live["workstations"][0]["summary"]["source_status"] == "live/fresh"
    assert saved

    monkeypatch.setattr(symbol_module, "_utc_now", lambda: now)
    monkeypatch.setattr(symbol_module, "_fetch_provider_history", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("unit timeout")))
    stale = build_symbol_workstation_contract(
        "MSFT",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        runtime_mode="live-if-available",
    )
    workstation = stale["workstations"][0]
    assert workstation["summary"]["source_status"] == "stale"
    assert workstation["history"][0]["fetched_at"] == fetched_at.isoformat()
    assert "unit timeout" in workstation["history"][0]["data_gap"]


def test_cache_mode_does_not_refresh_on_cache_miss(monkeypatch):
    calls = []
    monkeypatch.setattr(symbol_module, "_load_history_cache", lambda key: None)
    monkeypatch.setattr(symbol_module, "_fetch_provider_history", lambda *args, **kwargs: calls.append(args))

    contract = build_symbol_workstation_contract(
        "ETHUSDT",
        asset_class="crypto",
        interval="1h",
        range_name="5d",
        runtime_mode="cache",
    )

    workstation = contract["workstations"][0]
    assert workstation["history"] == []
    assert workstation["summary"]["status"] == "cache-miss"
    assert workstation["summary"]["source_status"] == "unavailable"
    assert workstation["summary"]["history_row_count"] == 0
    assert workstation["quote"]["provider"] == "Binance USD-M Futures"
    assert "live refresh was not attempted" in workstation["quote"]["data_gap"]
    assert calls == []


def test_live_provider_error_is_explicitly_unavailable_without_same_symbol_lkg(monkeypatch):
    monkeypatch.setattr(symbol_module, "_load_history_cache", lambda key: None)
    monkeypatch.setattr(symbol_module, "_fetch_provider_history", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("unit provider down")))

    contract = build_symbol_workstation_contract(
        "BTCUSDT",
        asset_class="crypto",
        interval="1d",
        range_name="3mo",
        runtime_mode="live-if-available",
    )

    workstation = contract["workstations"][0]
    assert workstation["history"] == []
    assert workstation["summary"]["status"] == "provider-error"
    assert workstation["summary"]["source_status"] == "unavailable"
    assert workstation["quote"]["provider"] == "Binance USD-M Futures"
    assert "unit provider down" in workstation["quote"]["data_gap"]


def test_phase5m_api_payloads_and_routes_are_json_safe():
    directory = build_api_symbol_directory_payload(query="micro", limit=5)
    workstation = build_api_symbol_workstation_payload(
        symbol="MSFT",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        runtime_mode="fixture",
    )

    for payload in (directory, workstation):
        valid, issues = validate_api_payload(payload)
        assert valid, issues
        encoded = json.dumps(payload)
        assert "AIza" not in encoded
        assert "sk-" not in encoded
        assert ".env" not in encoded
        assert "\\data\\private\\" not in encoded

    assert workstation["data"]["workstations"][0]["identity"]["symbol"] == "MSFT"
    assert directory["summary"]["result_count"] >= 1
    assert backend_app.get_symbol_workstation_payload(
        symbol="ETHUSDT",
        asset_class="crypto",
        interval="1d",
        range_name="3mo",
        runtime_mode="fixture",
    )["payload_type"] == "symbol_workstation"
    if backend_app.FASTAPI_AVAILABLE:
        paths = {route.path for route in backend_app.app.routes}
        assert "/api/symbol-directory" in paths
        assert "/api/symbol-workstation" in paths


def test_phase5m_web_contract_uses_interval_range_search_and_cross_surface_links():
    routes = (ROOT / "apps/web/src/lib/product-routes.ts").read_text(encoding="utf-8")
    page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    search = (ROOT / "apps/web/src/components/SymbolSearch.tsx").read_text(encoding="utf-8")
    workstation = (ROOT / "apps/web/src/components/SymbolWorkstation.tsx").read_text(encoding="utf-8")
    market_map = (ROOT / "apps/web/src/components/MarketMapScreener.tsx").read_text(encoding="utf-8")
    memory = (ROOT / "apps/web/src/components/ResearchMemoryWorkstation.tsx").read_text(encoding="utf-8")

    for marker in ["interval", "range", "assetClass", "symbol-workstation"]:
        assert marker in routes
    assert "SymbolSearch" in page
    assert "SymbolWorkstation" in page
    assert 'data-symbol-search-state="ready"' in search
    assert 'data-symbol-workstation-state=' in workstation
    assert "canonicalAssetHref" in market_map
    assert "canonicalAssetHref" in memory
