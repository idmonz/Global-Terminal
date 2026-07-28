from __future__ import annotations

import json
from pathlib import Path

import lib.market_discovery as discovery_module
import lib.market_map_screener as market_map_module
from lib.api_contracts import build_api_market_map_screener_payload, validate_api_payload
from lib.market_discovery import fetch_yahoo_us_market_snapshot
from lib.market_universe import parse_nasdaq_symbol_directory


ROOT = Path(__file__).resolve().parents[1]


NASDAQ_SAMPLE = """Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N
QQQ|Invesco QQQ Trust|Q|N|N|100|Y|N
ZTEST|Test Security|S|Y|N|100|N|N
File Creation Time: 0701202618:30|||||||
"""

OTHER_SAMPLE = """ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
IBM|International Business Machines Corporation|N|IBM|N|100|N|IBM
SPY|SPDR S&P 500 ETF Trust|P|SPY|Y|100|N|SPY
File Creation Time: 0701202618:31|||||||
"""


def test_nasdaq_directory_parser_keeps_authority_and_filters_test_rows():
    nasdaq = parse_nasdaq_symbol_directory(
        NASDAQ_SAMPLE,
        directory="nasdaq-listed",
        source_url="https://example.test/nasdaqlisted.txt",
        fetched_at="2026-07-01T18:31:00+00:00",
    )
    other = parse_nasdaq_symbol_directory(
        OTHER_SAMPLE,
        directory="other-listed",
        source_url="https://example.test/otherlisted.txt",
        fetched_at="2026-07-01T18:31:00+00:00",
    )

    assert [row["symbol"] for row in nasdaq["rows"]] == ["AAPL", "QQQ"]
    assert nasdaq["rows"][0]["mic"] == "XNAS"
    assert nasdaq["rows"][1]["security_type"] == "etf"
    assert nasdaq["directory_as_of"] == "2026-07-01T18:30:00"
    assert next(row for row in other["rows"] if row["symbol"] == "IBM")["mic"] == "XNYS"
    assert next(row for row in other["rows"] if row["symbol"] == "SPY")["mic"] == "ARCX"
    assert all(row["membership_source_status"] == "official/current-day" for row in nasdaq["rows"] + other["rows"])


def test_yahoo_market_snapshot_is_one_batch_and_preserves_nulls(monkeypatch):
    calls = []

    class FakeYf:
        @staticmethod
        def screen(query, size=250, sortField=None, sortAsc=None):
            calls.append((query, size, sortField, sortAsc))
            return {
                "quotes": [
                    {
                        "symbol": "AAA",
                        "longName": "Alpha",
                        "quoteType": "EQUITY",
                        "exchange": "NMS",
                        "marketCap": 500_000_000_000,
                        "regularMarketPrice": 125.0,
                        "regularMarketChangePercent": 1.5,
                        "regularMarketVolume": 2_000_000,
                        "averageDailyVolume3Month": 1_000_000,
                        "trailingPE": 20.0,
                    },
                    {
                        "symbol": "BBB",
                        "shortName": "Beta",
                        "quoteType": "EQUITY",
                        "exchange": "NYQ",
                        "marketCap": None,
                        "regularMarketPrice": None,
                        "regularMarketChangePercent": None,
                        "regularMarketVolume": None,
                        "averageDailyVolume3Month": None,
                    },
                ]
            }

    discovery_module._FINANCIAL_CACHE.clear()
    monkeypatch.setattr(discovery_module, "yf", FakeYf)
    monkeypatch.setattr(discovery_module, "EquityQuery", lambda *args: args)

    rows, status = fetch_yahoo_us_market_snapshot(limit=250)

    assert len(calls) == 1
    assert len(rows) == 2
    assert rows[0]["relative_volume"] == 2.0
    assert rows[1]["market_cap"] is None
    assert rows[1]["return_1d_pct"] is None
    assert status["source_status"] == "live/fresh"


def test_market_map_broadens_observations_without_fabricating_taxonomy_or_rank(monkeypatch):
    history_rows = [
        {
            "symbol": "AAA",
            "name": "Alpha",
            "asset_class": "equity",
            "sector": "Technology",
            "industry": "Software",
            "region": "United States",
            "exchange": "NASDAQ",
            "market_cap": 500_000_000_000,
            "size_value": 500_000_000_000,
            "price": 125.0,
            "return_1d_pct": 1.5,
            "return_1m_pct": 8.0,
            "realized_volatility_pct": 22.0,
            "drawdown_pct": -3.0,
            "rsi": 61.0,
            "price_vs_sma20_pct": 4.0,
            "above_20dma": True,
            "volume_zscore": 1.2,
            "market_data_as_of": "2026-07-01T20:00:00+00:00",
            "provider": "yfinance",
            "source_url": "https://finance.yahoo.com/quote/AAA",
            "fetched_at": "2026-07-01T20:01:00+00:00",
            "freshness": "live/fresh",
            "source_status": "live/fresh",
            "confidence": 0.9,
            "taxonomy_source_status": "static/proxy",
            "coordinate_method": "not_applicable",
            "caveat": "Delayed public history.",
            "data_gap": None,
            "not_financial_advice": True,
        }
    ]
    broad_rows = [
        {
            "symbol": symbol,
            "name": name,
            "exchange": exchange,
            "market_cap": cap,
            "price": price,
            "return_1d_pct": change,
            "volume": 1_000_000,
            "average_volume_3m": 800_000,
            "relative_volume": 1.25,
            "provider": "yahoo-screener",
            "source_url": f"https://finance.yahoo.com/quote/{symbol}",
            "fetched_at": "2026-07-01T20:02:00+00:00",
            "source_status": "live/fresh",
        }
        for symbol, name, exchange, cap, price, change in [
            ("AAA", "Alpha", "NMS", 510_000_000_000, 125.0, 1.5),
            ("BBB", "Beta", "NYQ", 80_000_000_000, 50.0, -0.5),
            ("CCC", "Gamma", "NMS", 10_000_000_000, 25.0, None),
        ]
    ]
    listing_rows = [
        {
            "symbol": symbol,
            "name": name,
            "exchange": exchange,
            "mic": mic,
            "security_type": "equity",
            "listing_status": "active",
            "membership_provider": "nasdaq_trader",
            "membership_source_url": "https://example.test/directory.txt",
            "membership_source_status": "official/current-day",
            "membership_as_of": "2026-07-01T18:30:00+00:00",
            "membership_caveat": "Official listing identity; not index membership.",
        }
        for symbol, name, exchange, mic in [
            ("AAA", "Alpha", "NASDAQ", "XNAS"),
            ("BBB", "Beta", "NYSE", "XNYS"),
            ("CCC", "Gamma", "NASDAQ", "XNAS"),
        ]
    ]
    runtime_status = {
        "provider": "yfinance",
        "status": "fresh",
        "fetched_at": "2026-07-01T20:01:00+00:00",
        "cached": False,
    }
    broad_status = {
        "provider": "yahoo-screener",
        "source_status": "live/fresh",
        "fetched_at": "2026-07-01T20:02:00+00:00",
        "row_count": 3,
    }
    listing_contract = {
        "rows": listing_rows,
        "sources": [],
        "summary": {
            "listing_count": 3,
            "source_status": "live/fresh",
            "directory_as_of": "2026-07-01T18:30:00+00:00",
        },
    }
    monkeypatch.setattr(market_map_module, "_runtime_rows", lambda period: (history_rows, runtime_status))
    monkeypatch.setattr(market_map_module, "fetch_yahoo_us_market_snapshot", lambda **kwargs: (broad_rows, broad_status))
    monkeypatch.setattr(market_map_module, "fetch_nasdaq_symbol_directory", lambda: listing_contract)
    monkeypatch.setattr(
        market_map_module,
        "fetch_sec_ticker_exchange_directory",
        lambda: {"rows": [], "source": {"provider": "sec_edgar", "source_status": "unavailable"}},
    )
    monkeypatch.setattr(
        market_map_module,
        "fetch_yahoo_sector_classification",
        lambda symbols: {
            "classification_version": "yahoo_sector_classification.v1",
            "rows": [],
            "sources": [],
            "summary": {"provider_call_count": 0},
        },
    )
    monkeypatch.setattr(
        market_map_module,
        "fetch_yahoo_batch_financial_snapshot",
        lambda symbols: ([], {**broad_status, "requested_symbol_count": len(list(symbols))}),
    )

    contract = market_map_module.build_market_map_screener_contract(include_runtime=True)
    rows = {row["symbol"]: row for row in contract["instruments"]}

    assert set(rows) == {"AAA", "BBB", "CCC"}
    assert rows["AAA"]["taxonomy"]["source_status"] == "static/proxy"
    assert rows["BBB"]["taxonomy"]["source_status"] == "unavailable"
    assert rows["BBB"]["sector"] == "Unclassified"
    assert rows["BBB"]["membership"]["source_status"] == "official/current-day"
    assert rows["BBB"]["return_1m_pct"] is None
    assert rows["BBB"]["rank_models"]["balanced"]["eligible"] is False
    assert contract["summary"]["instrument_count"] == 3
    assert contract["summary"]["official_listing_coverage_count"] == 3
    assert contract["summary"]["taxonomy_coverage_count"] == 1
    assert contract["readiness"]["authoritative_index_membership_claimed"] is False


def test_phase5z_market_map_payload_is_json_safe_and_secret_free():
    payload = build_api_market_map_screener_payload(include_runtime=False)
    valid, issues = validate_api_payload(payload)
    encoded = json.dumps(payload)

    assert valid, issues
    assert "universe_contract" in payload["data"]
    assert "AIza" not in encoded
    assert "sk-" not in encoded
    assert ".env" not in encoded


def test_phase5z_web_exposes_hierarchy_encoding_truth_and_local_url_state():
    component = (ROOT / "apps/web/src/components/MarketMapScreener.tsx").read_text(encoding="utf-8")
    page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    routes = (ROOT / "apps/web/src/lib/product-routes.ts").read_text(encoding="utf-8")
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    for marker in [
        "market-map-universe-strip",
        "official_listing_coverage_count",
        "taxonomy_coverage_count",
        "excluded_unverified_observation_count",
        "groupByHierarchy",
        'data-heatmap-size={sizeMetric}',
        'data-heatmap-color={colorMetric}',
        "window.history.replaceState",
        "Workstation unavailable",
        "exclusion_reasons",
        '["sector", "industry", "none"]',
        '["market_cap", "volume", "equal"]',
        '["return_1d_pct", "return_1m_pct", "relative_volume"]',
    ]:
        assert marker in component
    for param in ["industry", "country", "exchange", "eligibility", "group", "size", "color"]:
        assert f'"{param}"' in routes
    for selector in [
        ".market-map-universe-strip",
        ".market-map-display-controls",
        ".market-map-legend",
        ".market-map-rank-gap",
    ]:
        assert selector in css
    assert "useRouter" not in component
    assert 'activeFixture.runtime?.source === "runtime-api" ? apiBaseUrl : null' in page
    assert "universe.taxonomy_coverage_count ?? sectors.length" in page
