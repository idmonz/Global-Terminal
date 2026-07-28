from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from lib.api_contracts import validate_api_payload
from lib.symbol_intelligence import (
    align_comparison_history,
    build_market_clock,
    build_symbol_intelligence_contract,
    compute_symbol_technicals,
    filter_exact_symbol_news,
    panel_cache_key,
)


def _history(count: int = 80, *, symbol: str = "AAPL", start: float = 100.0):
    origin = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        close = start + index * 0.8 + (index % 5) * 0.15
        rows.append(
            {
                "date": (origin + timedelta(days=index)).isoformat(),
                "open": close - 0.4,
                "high": close + 1.2,
                "low": close - 1.1,
                "close": close,
                "volume": 1_000_000 + index * 1_000,
                "symbol": symbol,
                "provider": "unit-provider",
                "source_status": "live/fresh",
                "fetched_at": "2026-03-22T12:00:00+00:00",
            }
        )
    return rows


def test_market_clock_separates_retrieval_time_from_market_observation():
    rows = _history(2)
    rows[-1]["date"] = "2026-06-18T00:00:00+00:00"
    clock = build_market_clock(
        rows,
        asset_class="equity",
        interval="1d",
        source_status="live/fresh",
        retrieved_at="2026-06-22T07:56:44+00:00",
        now=datetime(2026, 6, 22, 8, 0, tzinfo=timezone.utc),
    )

    assert clock["retrieved_at"] == "2026-06-22T07:56:44+00:00"
    assert clock["market_data_as_of"] == "2026-06-18T00:00:00+00:00"
    assert clock["observation_age_seconds"] > 72 * 3600
    assert clock["market_data_status"] == "latest-session"
    assert clock["real_time_quote_claimed"] is False


def test_technical_panels_publish_bounded_formulas_and_minimum_observations():
    technicals = compute_symbol_technicals(_history(80), interval="1d")

    assert technicals["status"] == "available"
    assert technicals["summary"]["sma_20"] is not None
    assert technicals["summary"]["ema_50"] is not None
    assert 0 <= technicals["summary"]["rsi_14"] <= 100
    assert technicals["summary"]["macd_12_26_9"] is not None
    assert technicals["summary"]["realized_volatility_20"] >= 0
    assert technicals["summary"]["drawdown"] <= 0
    assert technicals["formula_version"]
    assert all(row["provider"] == "project-native/verified-history" for row in technicals["source_register"])

    insufficient = compute_symbol_technicals(_history(12), interval="1d")
    assert insufficient["status"] == "insufficient-history"
    assert insufficient["summary"]["sma_20"] is None
    assert insufficient["data_gap"]


def test_comparison_uses_timestamp_inner_join_and_reports_overlap():
    primary = _history(20, symbol="AAPL", start=100)
    comparison = _history(20, symbol="SPY", start=400)[5:]
    aligned = align_comparison_history(primary, comparison, primary_symbol="AAPL", comparison_symbol="SPY")

    assert aligned["status"] == "available"
    assert aligned["overlap_count"] == 15
    assert aligned["points"][0]["primary_return_pct"] == pytest.approx(0.0)
    assert aligned["points"][0]["comparison_return_pct"] == pytest.approx(0.0)
    assert aligned["alignment_method"] == "timestamp-inner-join"


def test_exact_news_matching_excludes_broad_market_rows():
    identity = {"symbol": "AAPL", "name": "Apple Inc.", "aliases": ["AAPL"]}
    rows = [
        {"title": "Apple expands developer tools", "summary": "AAPL product update", "source_url": "https://example.test/apple"},
        {"title": "US stocks rise before the open", "summary": "Technology shares advanced", "source_url": "https://example.test/market"},
        {"title": "Market wrap before the open", "summary": "Apple and banks were discussed", "source_url": "https://example.test/incidental"},
        {"title": "Pineapple harvest grows", "summary": "Agricultural markets", "source_url": "https://example.test/pineapple"},
    ]
    matches = filter_exact_symbol_news(rows, identity)

    assert [row["title"] for row in matches] == ["Apple expands developer tools"]
    assert matches[0]["match_terms"]
    assert matches[0]["exact_symbol_scope"] is True


def test_panel_cache_keys_partition_symbol_panel_formula_and_comparison():
    left = panel_cache_key("technical", "equity", "AAPL", "1d", "3mo", formula_version="v1")
    assert left != panel_cache_key("technical", "equity", "MSFT", "1d", "3mo", formula_version="v1")
    assert left != panel_cache_key("technical", "equity", "AAPL", "1d", "3mo", formula_version="v2")
    assert left != panel_cache_key("comparison", "equity", "AAPL", "1d", "3mo", formula_version="v1", compare="SPY")


def test_fixture_intelligence_is_json_safe_symbol_scoped_and_not_live():
    contract = build_symbol_intelligence_contract(
        "MSFT",
        asset_class="equity",
        interval="1d",
        range_name="3mo",
        runtime_mode="fixture",
        chart_type="candlestick",
        panels="trend,momentum,risk,news,financials",
        compare="SPY",
    )
    workstation = contract["workstations"][0]

    assert workstation["identity"]["symbol"] == "MSFT"
    assert workstation["market_clock"]["market_data_status"] == "fixture"
    assert workstation["chart_views"]["active_type"] == "candlestick"
    assert workstation["technical_analysis"]["summary"]["sma_20"] is not None
    assert workstation["financial_context"]["source_status"] == "fixture"
    assert workstation["exact_news"]["rows"] == []
    assert workstation["crypto_derivatives"]["availability"] == "not_applicable"
    assert workstation["comparison"]["comparison_symbol"] == "SPY"
    assert all(row["symbol"] == "MSFT" for row in workstation["history"])
    assert "AAPL" not in json.dumps(workstation)

    payload = {
        "contract_version": "phase_2b.v1",
        "payload_type": "symbol_workstation",
        "generated_at": "2026-06-22T00:00:00+00:00",
        "data": contract,
        "summary": contract["summary"],
        "source_status": contract["source_register"],
        "unavailable": contract["unavailable_sources"],
        "errors": [],
        "caveats": [],
    }
    valid, issues = validate_api_payload(payload)
    assert valid, issues


def test_etf_and_crypto_contexts_do_not_cross_asset_boundaries():
    spy = build_symbol_intelligence_contract("SPY", asset_class="etf", runtime_mode="fixture")
    btc = build_symbol_intelligence_contract("BTCUSDT", asset_class="crypto", runtime_mode="fixture")

    spy_row = spy["workstations"][0]
    btc_row = btc["workstations"][0]
    assert spy_row["financial_context"]["context_type"] == "fund-profile"
    assert spy_row["financial_context"]["company_statements_applicable"] is False
    assert btc_row["financial_context"]["availability"] == "not_applicable"
    assert btc_row["crypto_derivatives"]["availability"] == "fixture-unavailable"
    assert btc_row["crypto_derivatives"]["liquidation_coverage"] == "unavailable"


def test_live_api_alias_and_panel_provenance_are_additive(monkeypatch):
    from backend.api import app as backend_app
    import lib.symbol_intelligence as module

    monkeypatch.setattr(module, "_financial_context", lambda *args, **kwargs: {"availability": "unavailable", "context_type": "company-financials", "company_statements_applicable": True, "source_status": "unavailable", "provider": "unit", "fetched_at": "2026-06-22T00:00:00+00:00", "metrics": {}, "statements": {}, "sec_identity": None, "caveat": "unit", "data_gap": "unit", "not_financial_advice": True})
    monkeypatch.setattr(module, "_exact_news", lambda *args, **kwargs: {"availability": "exact-news-empty", "source_status": "unavailable", "provider": "unit", "source_url": None, "fetched_at": "2026-06-22T00:00:00+00:00", "rows": [], "match_terms": ["AAPL"], "caveat": "unit", "data_gap": "unit", "not_financial_advice": True})

    payload = backend_app.get_symbol_workstation_payload(symbol="AAPL", asset_class="equity", interval="1d", range_name="3mo", runtime_mode="fixture", chart_type="line", panels="trend,risk", compare="SPY")
    row = payload["data"]["workstations"][0]
    assert row["chart_views"]["active_type"] == "line"
    assert row["selected_panels"] == ["trend", "risk"]
    assert row["market_clock"]["market_data_as_of"]
    if backend_app.FASTAPI_AVAILABLE:
        assert "/api/symbol-intelligence" in {route.path for route in backend_app.app.routes}
