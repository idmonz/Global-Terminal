from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from lib.api_contracts import build_api_market_map_screener_payload
from lib.market_discovery import (
    fetch_yahoo_sector_classification,
    fetch_yahoo_us_market_snapshot,
)
from lib.market_snapshot_store import (
    build_market_snapshot_detail,
    compact_market_map_payload,
    materialize_market_snapshot,
    read_market_snapshot,
)
from lib.market_identity import (
    build_market_identity_contract,
    normalize_sec_ticker_exchange_rows,
)


def _listing(symbol: str, name: str, mic: str = "XNAS") -> dict:
    return {
        "symbol": symbol,
        "name": name,
        "asset_class": "equity",
        "security_type": "equity",
        "exchange": "NASDAQ" if mic == "XNAS" else "NYSE",
        "mic": mic,
        "listing_status": "active",
        "membership_provider": "nasdaq_trader",
        "membership_source_url": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
        "membership_source_status": "official/current-day",
        "membership_as_of": "2026-07-01T09:00:00",
        "membership_caveat": "Official listing identity; not index membership.",
    }


def test_sec_ticker_exchange_rows_preserve_cik_exchange_and_source_truth():
    payload = {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [
            [320193, "Apple Inc.", "AAPL", "Nasdaq"],
            [789019, "Microsoft Corp", "MSFT", "Nasdaq"],
            [None, "Broken", "", "NYSE"],
        ],
    }

    rows = normalize_sec_ticker_exchange_rows(
        payload,
        fetched_at="2026-07-01T10:00:00+00:00",
    )

    assert rows == [
        {
            "symbol": "AAPL",
            "cik": "0000320193",
            "sec_name": "Apple Inc.",
            "sec_exchange": "Nasdaq",
            "sec_provider": "sec_edgar",
            "sec_source_url": "https://www.sec.gov/files/company_tickers_exchange.json",
            "sec_source_status": "official/current",
            "sec_fetched_at": "2026-07-01T10:00:00+00:00",
        },
        {
            "symbol": "MSFT",
            "cik": "0000789019",
            "sec_name": "Microsoft Corp",
            "sec_exchange": "Nasdaq",
            "sec_provider": "sec_edgar",
            "sec_source_url": "https://www.sec.gov/files/company_tickers_exchange.json",
            "sec_source_status": "official/current",
            "sec_fetched_at": "2026-07-01T10:00:00+00:00",
        },
    ]


def test_identity_reconciliation_excludes_unsupported_security_types_and_is_deterministic():
    listing_contract = {
        "nasdaq_directory_version": "nasdaq_symbol_directory.v1",
        "rows": [
            _listing("AAPL", "Apple Inc. Common Stock"),
            _listing("BRK-B", "Berkshire Hathaway Inc. Class B", "XNYS"),
            _listing("ACME-W", "Acme Corp Warrant"),
            _listing("PREF", "Example 7.5% Preferred Stock", "XNYS"),
            _listing("ODD", "Odd Listing", "unknown"),
        ],
        "sources": [],
        "summary": {
            "source_status": "live/fresh",
            "directory_as_of": "2026-07-01T09:00:00",
            "authoritative_listing_identity": True,
        },
    }
    sec_rows = [
        {
            "symbol": "AAPL",
            "cik": "0000320193",
            "sec_name": "Apple Inc.",
            "sec_exchange": "Nasdaq",
            "sec_source_status": "official/current",
        }
    ]

    contract = build_market_identity_contract(
        listing_contract=listing_contract,
        sec_rows=sec_rows,
        generated_at="2026-07-01T10:00:00+00:00",
    )

    assert contract["identity_version"] == "market_identity.v1"
    assert [row["symbol"] for row in contract["rows"]] == ["AAPL", "BRK-B"]
    assert contract["rows"][0]["cik"] == "0000320193"
    assert contract["rows"][1]["cik"] is None
    assert contract["summary"]["supported_count"] == 2
    assert contract["summary"]["excluded_count"] == 3
    assert contract["summary"]["authoritative_index_membership"] is False
    assert {row["reason"] for row in contract["exclusions"]} == {
        "unsupported-security-type",
        "unsupported-exchange",
    }


def test_broad_screener_uses_bounded_pages_and_deduplicates(monkeypatch):
    calls = []

    class FakeYf:
        @staticmethod
        def screen(query, **kwargs):
            calls.append(dict(kwargs))
            offset = kwargs.get("offset", 0)
            return {
                "total": 900,
                "quotes": [
                    {
                        "symbol": "S000" if offset == 250 and index == 0 else f"S{offset + index:03d}",
                        "longName": f"Security {offset + index}",
                        "quoteType": "EQUITY",
                        "region": "us",
                        "marketCap": 10_000_000_000 - offset - index,
                        "regularMarketPrice": 100,
                        "regularMarketChangePercent": 1,
                    }
                    for index in range(250)
                ],
            }

    import lib.market_discovery as module

    module._FINANCIAL_CACHE.clear()
    monkeypatch.setattr(module, "yf", FakeYf)
    monkeypatch.setattr(module, "EquityQuery", lambda *args: args)

    rows, status = fetch_yahoo_us_market_snapshot(limit=600, page_size=250)

    assert len(calls) == 3
    assert [call.get("offset", 0) for call in calls] == [0, 250, 500]
    assert len(rows) == 599
    assert len({row["symbol"] for row in rows}) == 599
    assert status["provider_call_count"] == 3
    assert status["page_count"] == 3
    assert status["requested_limit"] == 600


def test_sector_classification_is_batched_and_never_claims_gics(monkeypatch):
    calls = []

    class FakeYf:
        @staticmethod
        def screen(query, **kwargs):
            calls.append((query, kwargs))
            sector = query[1][1][1][1] if isinstance(query, tuple) else "Technology"
            symbol = "AAPL" if sector == "Technology" else "JPM"
            return {"quotes": [{"symbol": symbol}], "total": 1}

    import lib.market_discovery as module

    module._SECTOR_CACHE.clear()
    monkeypatch.setattr(module, "yf", FakeYf)
    monkeypatch.setattr(module, "EquityQuery", lambda *args: args)
    monkeypatch.setattr(module, "YAHOO_SECTORS", ("Technology", "Financial Services"))

    contract = fetch_yahoo_sector_classification({"AAPL", "JPM", "UNKNOWN"})

    assert len(calls) == 2
    assert {row["symbol"] for row in contract["rows"]} == {"AAPL", "JPM"}
    assert all(row["source_status"] == "provider-classification" for row in contract["rows"])
    assert all(row["taxonomy_authoritative"] is False for row in contract["rows"])
    assert contract["summary"]["classified_count"] == 2
    assert contract["summary"]["unclassified_count"] == 1
    assert contract["summary"]["provider_call_count"] == 2


def test_compact_snapshot_scales_past_300_rows_and_detail_sidecar_retains_evidence(tmp_path):
    payload = build_api_market_map_screener_payload(include_runtime=False)
    template = payload["data"]["instruments"][0]
    rows = []
    for index in range(333):
        row = deepcopy(template)
        row["symbol"] = f"T{index:03d}"
        row["name"] = f"Test Security {index}"
        if index >= 60:
            for model in row.get("rank_models", {}).values():
                model["eligible"] = False
                model["score"] = None
                model["rank"] = None
        rows.append(row)
    payload["data"]["instruments"] = rows
    payload["data"]["heatmap_tiles"] = deepcopy(rows)
    payload["data"]["ranked_rows"] = deepcopy(rows[:60])
    payload["summary"]["instrument_count"] = len(rows)

    compact = compact_market_map_payload(payload)
    encoded = json.dumps(compact, separators=(",", ":")).encode()
    materialize_market_snapshot(payload, base_dir=tmp_path)
    loaded = read_market_snapshot(base_dir=tmp_path)
    detail = build_market_snapshot_detail("T100", base_dir=tmp_path)

    assert len(compact["data"]["instruments"]) == 333
    assert len(encoded) < 900_000
    assert loaded["data"]["instruments"][100]["rank_models"] == {}
    assert detail["data"]["instrument"]["rank_models"]
    assert detail["summary"]["symbol"] == "T100"


def test_phase6b_web_exposes_classification_and_refresh_history_truth():
    root = Path(__file__).resolve().parents[1]
    component = (root / "apps/web/src/components/MarketMapScreener.tsx").read_text(encoding="utf-8")
    css = (root / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    for marker in [
        "data-market-map-industry-coverage",
        "data-market-map-provider-taxonomy",
        "data-market-map-taxonomy-conflicts",
        "data-market-refresh-history",
        "local_taxonomy_coverage_count",
        "provider_taxonomy_coverage_count",
        "industry_coverage_count",
        "market-map-refresh-ledger",
    ]:
        assert marker in component
    assert ".market-map-refresh-ledger" in css
