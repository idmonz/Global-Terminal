from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

import lib.symbol_intelligence as intelligence_module
import lib.symbol_workstation as workstation_module
from lib.market_snapshot_store import materialize_market_snapshot


UTC = timezone.utc


def _instrument(
    symbol: str,
    name: str,
    *,
    sector: str,
    exchange: str,
    mic: str,
    cik: str,
) -> dict:
    return {
        "symbol": symbol,
        "name": name,
        "asset_class": "equity",
        "exchange": exchange,
        "mic": mic,
        "region": "United States",
        "country": "United States",
        "sector": sector,
        "industry": "Unclassified",
        "market_cap": 500_000_000_000.0,
        "price": 250.0,
        "return_1d_pct": 1.25,
        "forward_pe": 22.0,
        "trailing_pe": 25.0,
        "price_to_book": 7.0,
        "eps_ttm": 10.0,
        "eps_forward": 11.0,
        "source_status": "live/fresh",
        "fetched_at": "2026-07-02T00:00:00+00:00",
        "market_data_as_of": "2026-07-01T20:00:00+00:00",
        "provider": "unit-market-provider",
        "source_url": f"https://example.test/market/{symbol}",
        "membership": {
            "provider": "unit-official-listing",
            "source_status": "official/current-day",
            "source_url": f"https://example.test/listing/{symbol}",
            "as_of": "2026-07-02T00:00:00+00:00",
            "listing_status": "active",
            "exchange": exchange,
            "mic": mic,
            "security_type": "equity",
            "cik": cik,
            "sec_source_status": "official/current",
            "identity_conflict": False,
            "caveat": "Official identity test row; no index membership is claimed.",
        },
        "taxonomy": {
            "provider": "unit-sector-provider",
            "source_status": "provider-classification",
            "source_url": f"https://example.test/taxonomy/{symbol}",
            "classification_version": "unit-sector.v1",
            "reviewed_at": "2026-07-02T00:00:00+00:00",
            "sector": sector,
            "industry": None,
            "provider_sector": sector,
            "taxonomy_authoritative": False,
            "classification_conflict": False,
            "caveat": "Provider classification is not official GICS.",
        },
        "financial_snapshot": {
            "provider": "unit-market-provider",
            "source_status": "live/fresh",
            "source_url": f"https://example.test/market/{symbol}",
            "fetched_at": "2026-07-02T00:00:00+00:00",
        },
        "factors": {
            "market_cap": 500_000_000_000.0,
            "forward_pe": 22.0,
            "trailing_pe": 25.0,
            "price_to_book": 7.0,
            "eps_ttm": 10.0,
            "eps_forward": 11.0,
            "valuation_available": True,
        },
        "caveat": "Delayed market observation.",
        "data_gap": "On-demand history has not been fetched.",
        "not_financial_advice": True,
    }


def _snapshot_payload() -> dict:
    return {
        "contract_version": "phase_2b.v1",
        "payload_type": "market_map_screener",
        "generated_at": "2026-07-02T00:00:00+00:00",
        "data": {
            "workspace": "market-map-screener",
            "instruments": [
                _instrument(
                    "TSLA",
                    "Tesla, Inc.",
                    sector="Consumer Discretionary",
                    exchange="NASDAQ Global Select",
                    mic="XNAS",
                    cik="0001318605",
                ),
                _instrument(
                    "JNJ",
                    "Johnson & Johnson",
                    sector="Health Care",
                    exchange="NYSE",
                    mic="XNYS",
                    cik="0000200406",
                ),
            ],
            "source_register": [],
        },
        "summary": {"instrument_count": 2},
        "source_status": [],
        "unavailable": [],
        "errors": [],
        "caveats": [],
    }


def _materialize(tmp_path) -> None:
    materialize_market_snapshot(
        _snapshot_payload(),
        base_dir=tmp_path,
        now=datetime(2026, 7, 2, tzinfo=UTC),
    )


def test_materialized_identity_activates_exact_dynamic_symbol(tmp_path):
    _materialize(tmp_path)

    identity = workstation_module.resolve_symbol(
        "TSLA",
        asset_class="equity",
        snapshot_base_dir=tmp_path,
    )
    contract = workstation_module.build_symbol_workstation_contract(
        "TSLA",
        asset_class="equity",
        runtime_mode="fixture",
        snapshot_base_dir=tmp_path,
    )

    assert identity is not None
    assert identity["symbol"] == "TSLA"
    assert identity["name"] == "Tesla, Inc."
    assert identity["cik"] == "0001318605"
    assert identity["mic"] == "XNAS"
    assert identity["identity_origin"] == "materialized-market-snapshot"
    assert identity["market_map_context"]["sector"] == "Consumer Discretionary"
    assert contract["workstations"][0]["identity"]["symbol"] == "TSLA"
    assert contract["workstations"][0]["capability_plan"]["broad_universe_rebuild"] is False
    assert all(row["symbol"] == "TSLA" for row in contract["workstations"][0]["history"])
    assert '"symbol": "AAPL"' not in json.dumps(contract)


def test_runtime_directory_merges_materialized_identities_without_duplicate_static_rows(tmp_path):
    _materialize(tmp_path)

    static = workstation_module.symbol_identities(include_materialized=False)
    runtime = workstation_module.symbol_identities(
        include_materialized=True,
        snapshot_base_dir=tmp_path,
    )
    symbols = [row["symbol"] for row in runtime]

    assert len(runtime) >= len(static)
    assert symbols.count("TSLA") == 1
    assert symbols.count("JNJ") == 1
    by_symbol = {row["symbol"]: row for row in runtime}
    assert by_symbol["TSLA"]["identity_origin"] == "materialized-market-snapshot"
    assert by_symbol["JNJ"]["identity_origin"] == "materialized-market-snapshot"
    assert by_symbol["TSLA"]["local_registry_evidence"]["source"]
    assert by_symbol["JNJ"]["local_registry_evidence"]["source"]
    assert workstation_module.search_symbols(
        "Tesla",
        asset_class="equity",
        include_materialized=True,
        snapshot_base_dir=tmp_path,
    )[0]["symbol"] == "TSLA"


def test_dynamic_cache_and_live_failure_remain_same_symbol_or_explicitly_unavailable(
    monkeypatch,
    tmp_path,
):
    _materialize(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(workstation_module, "_load_history_cache", lambda _key: None)
    monkeypatch.setattr(
        workstation_module,
        "_fetch_provider_history",
        lambda identity, *_: calls.append(identity["symbol"])
        or (_ for _ in ()).throw(TimeoutError("provider down")),
    )

    failed = workstation_module.build_symbol_workstation_contract(
        "JNJ",
        asset_class="equity",
        runtime_mode="live-if-available",
        snapshot_base_dir=tmp_path,
    )
    row = failed["workstations"][0]

    assert calls == ["JNJ"]
    assert row["history"] == []
    assert row["summary"]["source_status"] == "unavailable"
    assert row["summary"]["status"] == "provider-error"
    assert row["quote"]["last_price"] == 250.0
    assert "same-symbol" in row["quote"]["caveat"].lower()
    assert row["identity"]["symbol"] == "JNJ"
    assert "AAPL" not in json.dumps(failed)


def test_cache_mode_never_calls_selected_symbol_or_broad_refresh_providers(
    monkeypatch,
    tmp_path,
):
    _materialize(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(workstation_module, "_load_history_cache", lambda _key: None)
    monkeypatch.setattr(intelligence_module, "load_runtime_cache_record", lambda _key: None)
    monkeypatch.setattr(
        workstation_module,
        "_fetch_provider_history",
        lambda *_args, **_kwargs: calls.append("history"),
    )
    monkeypatch.setattr(
        intelligence_module,
        "_fetch_financial_context",
        lambda *_args, **_kwargs: calls.append("financial"),
    )
    monkeypatch.setattr(
        intelligence_module,
        "_normalize_yfinance_news",
        lambda *_args, **_kwargs: calls.append("news"),
    )

    contract = intelligence_module.build_symbol_intelligence_contract(
        "TSLA",
        asset_class="equity",
        runtime_mode="cache",
        snapshot_base_dir=tmp_path,
    )
    row = contract["workstations"][0]

    assert calls == []
    assert row["identity"]["symbol"] == "TSLA"
    assert row["financial_context"]["metrics"]["market_cap"] == 500_000_000_000.0
    assert row["financial_context"]["availability"] == "market-snapshot-only"
    assert row["exact_news"]["availability"] == "unavailable"


def test_malformed_unknown_and_asset_class_mismatch_do_not_activate_snapshot_rows(
    monkeypatch,
    tmp_path,
):
    _materialize(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(
        workstation_module,
        "_fetch_provider_history",
        lambda *_args, **_kwargs: calls.append("provider"),
    )

    malformed = workstation_module.build_symbol_workstation_contract(
        "../TSLA",
        asset_class="equity",
        runtime_mode="live-if-available",
        snapshot_base_dir=tmp_path,
    )
    unknown = workstation_module.build_symbol_workstation_contract(
        "ZZZZ",
        asset_class="equity",
        runtime_mode="live-if-available",
        snapshot_base_dir=tmp_path,
    )
    mismatch = workstation_module.build_symbol_workstation_contract(
        "TSLA",
        asset_class="crypto",
        runtime_mode="live-if-available",
        snapshot_base_dir=tmp_path,
    )

    assert malformed["summary"]["status"] == "unknown-symbol"
    assert unknown["summary"]["status"] == "unknown-symbol"
    assert mismatch["summary"]["status"] == "asset-class-mismatch"
    assert calls == []
    assert "AAPL" not in json.dumps([malformed, unknown, mismatch])


def test_unsupported_capability_has_zero_provider_budget(monkeypatch, tmp_path):
    _materialize(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(workstation_module, "_load_history_cache", lambda _key: None)
    monkeypatch.setattr(intelligence_module, "load_runtime_cache_record", lambda _key: None)
    monkeypatch.setattr(
        workstation_module,
        "_fetch_provider_history",
        lambda *_args, **_kwargs: calls.append("history"),
    )
    monkeypatch.setattr(
        intelligence_module,
        "_fetch_financial_context",
        lambda *_args, **_kwargs: calls.append("financial"),
    )
    monkeypatch.setattr(
        intelligence_module,
        "_normalize_yfinance_news",
        lambda *_args, **_kwargs: calls.append("news"),
    )

    contract = intelligence_module.build_symbol_intelligence_contract(
        "TSLA",
        asset_class="equity",
        interval="15m",
        range_name="1y",
        runtime_mode="live-if-available",
        snapshot_base_dir=tmp_path,
    )
    row = contract["workstations"][0]

    assert row["summary"]["status"] == "unsupported-interval"
    assert row["capability_plan"]["maximum_provider_calls"] == 0
    assert row["capability_plan"]["request_supported"] is False
    assert calls == []


def test_exact_symbol_http_route_is_etagged_and_unknown_isolated(monkeypatch, tmp_path):
    from backend.api import app as backend_app

    if not backend_app.FASTAPI_AVAILABLE:
        pytest.skip("FastAPI is optional.")
    from fastapi.testclient import TestClient

    _materialize(tmp_path)
    monkeypatch.setenv("MARKET_SNAPSHOT_DIR", str(tmp_path))
    client = TestClient(backend_app.app)

    first = client.get(
        "/api/symbol-workstation/TSLA",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
    )
    assert first.status_code == 200
    assert first.headers["etag"]
    assert first.json()["data"]["workstations"][0]["identity"]["symbol"] == "TSLA"

    repeated = client.get(
        "/api/symbol-workstation/TSLA",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
        headers={"If-None-Match": first.headers["etag"]},
    )
    assert repeated.status_code == 304

    unknown = client.get(
        "/api/symbol-workstation/ZZZZ",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
    )
    assert unknown.status_code == 404
    assert unknown.json()["summary"]["symbol"] == "ZZZZ"
    assert "AAPL" not in unknown.text
