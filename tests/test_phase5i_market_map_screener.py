from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import lib.market_map_screener as market_map_module
from backend.api import app as backend_app
from lib.api_contracts import build_api_market_map_screener_payload, validate_api_payload
from lib.data_status import success
from lib.market_map_screener import (
    MARKET_MAP_SCREENER_VERSION,
    build_market_map_screener_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def _runtime_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "company": "Apple",
                "sector": "Information Technology",
                "industry": "Technology Hardware",
                "market_cap": 2_900_000_000_000,
                "price": 210.0,
                "return_1d_pct": 1.2,
                "return_1w_pct": 2.4,
                "return_1m_pct": 5.5,
                "realized_volatility_pct": 24.0,
                "drawdown_pct": -4.0,
                "rsi": 58.0,
                "volume_zscore": 0.8,
                "range_52w_position": 82.0,
                "data_status": "real/delayed yfinance",
            },
            {
                "ticker": "MSFT",
                "company": "Microsoft",
                "sector": "Information Technology",
                "industry": "Software",
                "market_cap": 3_200_000_000_000,
                "price": 480.0,
                "return_1d_pct": None,
                "return_1w_pct": None,
                "return_1m_pct": None,
                "realized_volatility_pct": None,
                "drawdown_pct": None,
                "rsi": None,
                "volume_zscore": None,
                "range_52w_position": None,
                "data_status": "price data unavailable",
            },
        ]
    )


def _stub_broad_sources(monkeypatch, frame: pd.DataFrame) -> None:
    broad_rows = []
    listing_rows = []
    for item in frame.to_dict(orient="records"):
        symbol = item["ticker"]
        broad_rows.append(
            {
                "symbol": symbol,
                "name": item["company"],
                "asset_class": "equity",
                "exchange": "NASDAQ",
                "market_cap": item.get("market_cap"),
                "price": item.get("price"),
                "return_1d_pct": item.get("return_1d_pct"),
                "volume": 1_000_000,
                "average_volume_3m": 900_000,
                "relative_volume": 1.1111,
                "market_data_as_of": "2026-07-01T20:00:00+00:00",
                "provider": "yahoo-screener",
                "source_url": f"https://finance.yahoo.com/quote/{symbol}",
                "fetched_at": "2026-07-01T20:01:00+00:00",
                "source_status": "live/fresh",
            }
        )
        listing_rows.append(
            {
                "symbol": symbol,
                "membership_provider": "nasdaq_trader",
                "membership_source_url": "https://example.test/nasdaqlisted.txt",
                "membership_source_status": "official/current-day",
                "membership_as_of": "2026-07-01T18:30:00",
                "listing_status": "active",
                "financial_status_code": "N",
                "exchange": "NASDAQ",
                "mic": "XNAS",
                "security_type": "equity",
                "membership_caveat": "Official listing identity; not index membership.",
            }
        )
    monkeypatch.setattr(
        market_map_module,
        "fetch_yahoo_us_market_snapshot",
        lambda **kwargs: (
            broad_rows,
            {
                "provider": "yahoo-screener",
                "source_status": "live/fresh",
                "fetched_at": "2026-07-01T20:01:00+00:00",
                "row_count": len(broad_rows),
            },
        ),
    )
    monkeypatch.setattr(
        market_map_module,
        "fetch_nasdaq_symbol_directory",
        lambda: {
            "rows": listing_rows,
            "sources": [],
            "summary": {
                "listing_count": len(listing_rows),
                "source_status": "live/fresh",
                "directory_as_of": "2026-07-01T18:30:00",
                "authoritative_listing_identity": True,
            },
        },
    )
    monkeypatch.setattr(
        market_map_module,
        "fetch_yahoo_batch_financial_snapshot",
        lambda symbols: (
            [],
            {
                "provider": "yahoo-screener",
                "source_status": "live/fresh",
                "fetched_at": "2026-07-01T20:01:00+00:00",
                "row_count": 0,
                "requested_symbol_count": len(list(symbols)),
            },
        ),
    )
    monkeypatch.setattr(
        market_map_module,
        "fetch_sec_ticker_exchange_directory",
        lambda: {
            "rows": [],
            "source": {"provider": "sec_edgar", "source_status": "unavailable"},
        },
    )
    monkeypatch.setattr(
        market_map_module,
        "fetch_yahoo_sector_classification",
        lambda symbols: {
            "classification_version": "yahoo_sector_classification.v2",
            "rows": [],
            "sources": [],
            "summary": {
                "provider_call_count": 0,
                "classified_count": 0,
                "unclassified_count": len(list(symbols)),
            },
        },
    )


def test_runtime_market_map_normalizes_provenance_and_does_not_zero_rank_missing(monkeypatch):
    frame = _runtime_frame()
    status = success(frame, source="AAPL,MSFT", provider="yfinance", stale_after_seconds=900)
    monkeypatch.setattr("lib.market_map_screener.build_stock_screener", lambda period="3mo": (frame, status))
    _stub_broad_sources(monkeypatch, frame)

    contract = build_market_map_screener_contract(include_runtime=True, period="3mo")

    assert contract["market_map_screener_version"] == MARKET_MAP_SCREENER_VERSION
    assert len(contract["instruments"]) == 2
    apple = next(row for row in contract["instruments"] if row["symbol"] == "AAPL")
    missing = next(row for row in contract["instruments"] if row["symbol"] == "MSFT")
    assert apple["source_status"] == "live/fresh"
    assert apple["coordinate_method"] == "not_applicable"
    assert apple["rank_eligible"] is True
    assert missing["rank_eligible"] is False
    assert missing["rank_score"] is None
    assert all(row["not_financial_advice"] is True for row in contract["instruments"])
    assert all(row["provider"] and row["source_url"] and row["fetched_at"] for row in contract["instruments"])


def test_fixture_market_map_is_deterministic_json_safe_and_explicitly_fixture():
    contract = build_market_map_screener_contract(include_runtime=False)
    payload = build_api_market_map_screener_payload(include_runtime=False)

    assert contract["instruments"]
    assert contract["heatmap_tiles"]
    assert contract["sector_summaries"]
    assert contract["filter_options"]["sectors"]
    assert contract["readiness"]["live_universe_claimed"] is False
    assert all(row["source_status"] == "fixture" for row in contract["instruments"])
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    encoded = json.dumps(payload)
    assert "AIza" not in encoded
    assert "sk-" not in encoded
    assert ".env" not in encoded


def test_market_map_sector_counts_and_ranked_rows_match_instruments(monkeypatch):
    frame = _runtime_frame().iloc[[0]].copy()
    status = success(frame, source="AAPL", provider="yfinance", stale_after_seconds=900)
    monkeypatch.setattr("lib.market_map_screener.build_stock_screener", lambda period="3mo": (frame, status))
    _stub_broad_sources(monkeypatch, frame)

    contract = build_market_map_screener_contract(include_runtime=True)

    assert sum(row["instrument_count"] for row in contract["sector_summaries"]) == len(contract["instruments"])
    assert len(contract["ranked_rows"]) == 1
    assert contract["scatter_points"][0]["symbol"] == "AAPL"
    assert contract["summary"]["ranked_count"] == 1


def test_runtime_market_map_uses_ttl_cache_and_single_fetch(monkeypatch):
    frame = _runtime_frame().iloc[[0]].copy()
    status = success(frame, source="AAPL", provider="yfinance", stale_after_seconds=900)
    calls = []

    def provider(period="3mo"):
        calls.append(period)
        return frame, status

    market_map_module._RUNTIME_CACHE.clear()
    monkeypatch.setattr(market_map_module, "build_stock_screener", provider)
    monkeypatch.setattr(market_map_module.time, "monotonic", iter([0.0, 10.0]).__next__)
    _stub_broad_sources(monkeypatch, frame)

    first = build_market_map_screener_contract(include_runtime=True)
    second = build_market_map_screener_contract(include_runtime=True)

    assert len(calls) == 1
    assert first["instruments"][0]["history_source_status"] == "live/fresh"
    assert second["instruments"][0]["history_source_status"] == "cached"


def test_runtime_market_map_uses_labeled_stale_fallback_after_refresh_failure(monkeypatch):
    frame = _runtime_frame().iloc[[0]].copy()
    status = success(frame, source="AAPL", provider="yfinance", stale_after_seconds=900)
    calls = 0

    def provider(period="3mo"):
        nonlocal calls
        calls += 1
        if calls == 1:
            return frame, status
        raise TimeoutError("unit timeout")

    market_map_module._RUNTIME_CACHE.clear()
    monkeypatch.setattr(market_map_module, "build_stock_screener", provider)
    monkeypatch.setattr(market_map_module.time, "monotonic", iter([0.0, 700.0]).__next__)
    _stub_broad_sources(monkeypatch, frame)

    build_market_map_screener_contract(include_runtime=True)
    stale = build_market_map_screener_contract(include_runtime=True)

    assert stale["instruments"][0]["history_source_status"] == "stale"
    assert "unit timeout" in stale["instruments"][0]["data_gap"]
    assert stale["summary"]["source_status"] == "live/fresh"


def test_fastapi_market_map_route_is_registered_and_valid():
    payload = backend_app.get_market_map_screener_payload(include_runtime=False)
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    assert payload["payload_type"] == "market_map_screener"
    if backend_app.FASTAPI_AVAILABLE:
        paths = {route.path for route in backend_app.app.routes}
        assert "/api/market-map-screener" in paths


def test_nextjs_has_product_first_market_map_url_state_and_visual_surfaces():
    page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    component = (ROOT / "apps/web/src/components/MarketMapScreener.tsx").read_text(encoding="utf-8")
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    for marker in [
        'requestedView === "market-map"',
        'data-product-view="market-map-screener"',
        "MarketMapScreener",
        'active="market-map"',
    ]:
        assert marker in page
    for marker in [
        "useSearchParams",
        "window.history.replaceState",
        '"sector"',
        '"industry"',
        '"selected"',
        '"compare"',
        'data-market-map-state="ready"',
        "market-map-heatmap",
        "market-map-scatter",
        "market-map-ranked-table",
    ]:
        assert marker in component
    assert "useRouter" not in component
    for marker in [
        ".market-map-product",
        ".market-map-heatmap",
        ".market-map-ranked-table",
        ".market-map-scatter",
        ".market-map-mobile-controls",
    ]:
        assert marker in css
