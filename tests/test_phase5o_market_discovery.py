from __future__ import annotations

import json

from lib.api_contracts import build_api_market_map_screener_payload, validate_api_payload
from lib.market_discovery import (
    DISCOVERY_VERSION,
    apply_discovery_filters,
    enrich_discovery_rows,
    fetch_yahoo_batch_financial_snapshot,
)


def _rows():
    return [
        {
            "symbol": "AAA",
            "name": "Alpha",
            "sector": "Technology",
            "market_cap": 500_000_000_000,
            "return_1d_pct": 1.5,
            "return_1m_pct": 8.0,
            "realized_volatility_pct": 22.0,
            "drawdown_pct": -3.0,
            "rsi": 61.0,
            "price_vs_sma20_pct": 4.0,
            "above_20dma": True,
            "volume_zscore": 1.2,
            "market_data_as_of": "2026-06-20T00:00:00+00:00",
            "provider": "yfinance",
            "source_status": "live/fresh",
            "fetched_at": "2026-06-22T00:00:00+00:00",
        },
        {
            "symbol": "BBB",
            "name": "Beta",
            "sector": "Financials",
            "market_cap": 90_000_000_000,
            "return_1d_pct": -0.5,
            "return_1m_pct": 2.0,
            "realized_volatility_pct": 16.0,
            "drawdown_pct": -8.0,
            "rsi": 48.0,
            "price_vs_sma20_pct": -1.0,
            "above_20dma": False,
            "volume_zscore": 0.1,
            "market_data_as_of": "2026-06-20T00:00:00+00:00",
            "provider": "yfinance",
            "source_status": "live/fresh",
            "fetched_at": "2026-06-22T00:00:00+00:00",
        },
        {
            "symbol": "CCC",
            "name": "Gamma",
            "sector": "Technology",
            "market_cap": 8_000_000_000,
            "return_1d_pct": None,
            "return_1m_pct": None,
            "realized_volatility_pct": None,
            "drawdown_pct": None,
            "rsi": None,
            "price_vs_sma20_pct": None,
            "above_20dma": None,
            "volume_zscore": None,
            "market_data_as_of": None,
            "provider": "yfinance",
            "source_status": "unavailable",
            "fetched_at": "2026-06-22T00:00:00+00:00",
        },
    ]


def _financials():
    return [
        {
            "symbol": "AAA",
            "market_cap": 510_000_000_000,
            "trailing_pe": 25.0,
            "forward_pe": 22.0,
            "price_to_book": 8.0,
            "eps_ttm": 6.5,
            "eps_forward": 7.2,
            "financial_provider": "yahoo-screener",
            "financial_source_status": "live/fresh",
        },
        {
            "symbol": "BBB",
            "market_cap": 92_000_000_000,
            "trailing_pe": 12.0,
            "forward_pe": 11.0,
            "price_to_book": 1.4,
            "eps_ttm": 4.0,
            "eps_forward": 4.2,
            "financial_provider": "yahoo-screener",
            "financial_source_status": "live/fresh",
        },
    ]


def test_discovery_enrichment_builds_four_reconciling_rank_models():
    result = enrich_discovery_rows(_rows(), _financials())

    assert result["discovery_version"] == DISCOVERY_VERSION
    assert set(result["rank_models"]) == {"balanced", "momentum", "risk_adjusted", "quality"}
    alpha = next(row for row in result["rows"] if row["symbol"] == "AAA")
    for model_id in result["rank_models"]:
        model = alpha["rank_models"][model_id]
        if model["eligible"]:
            contribution_sum = round(sum(item["contribution"] for item in model["contributions"]), 2)
            assert abs(contribution_sum - model["score"]) <= 0.02
            assert model["rank"] >= 1
    assert alpha["factors"]["valuation_available"] is True
    assert alpha["market_clock"]["market_data_as_of"] == "2026-06-20T00:00:00+00:00"


def test_missing_required_factors_are_excluded_not_imputed():
    result = enrich_discovery_rows(_rows(), _financials())
    missing = next(row for row in result["rows"] if row["symbol"] == "CCC")

    assert missing["rank_models"]["balanced"]["eligible"] is False
    assert missing["rank_models"]["balanced"]["score"] is None
    assert "return_1m_pct" in missing["rank_models"]["balanced"]["exclusion_reasons"]
    assert missing["factors"]["trailing_pe"] is None


def test_composable_filters_cover_technical_financial_risk_and_quality():
    rows = enrich_discovery_rows(_rows(), _financials())["rows"]
    filtered = apply_discovery_filters(
        rows,
        {
            "sectors": ["Technology"],
            "market_cap": "mega",
            "return_1m": "positive",
            "volatility": "moderate",
            "rsi": "constructive",
            "trend": "above-sma20",
            "valuation": "available",
            "quality": "complete",
            "rank": "balanced",
        },
    )

    assert [row["symbol"] for row in filtered] == ["AAA"]


def test_yahoo_batch_financial_snapshot_uses_one_screener_call(monkeypatch):
    calls = []

    class FakeYf:
        @staticmethod
        def screen(query, size=250, sortField=None, sortAsc=None):
            calls.append((query, size, sortField, sortAsc))
            return {
                "quotes": [
                    {
                        "symbol": "AAA",
                        "marketCap": 500,
                        "trailingPE": 20,
                        "forwardPE": 18,
                        "priceToBook": 4,
                        "epsTrailingTwelveMonths": 5,
                        "epsForward": 6,
                        "exchangeDataDelayedBy": 15,
                    },
                    {"symbol": "OTHER", "marketCap": 1},
                ]
            }

    monkeypatch.setattr("lib.market_discovery.yf", FakeYf)
    rows, status = fetch_yahoo_batch_financial_snapshot(["AAA", "BBB"])

    assert len(calls) == 1
    assert [row["symbol"] for row in rows] == ["AAA"]
    assert rows[0]["trailing_pe"] == 20.0
    assert status["source_status"] == "live/fresh"


def test_market_map_api_remains_json_safe_and_adds_discovery_contract():
    payload = build_api_market_map_screener_payload(include_runtime=False)
    valid, issues = validate_api_payload(payload)

    assert valid, issues
    assert payload["data"]["discovery_version"] == DISCOVERY_VERSION
    assert payload["data"]["factor_catalog"]
    assert payload["data"]["rank_models"]
    encoded = json.dumps(payload)
    assert "AIza" not in encoded
    assert "sk-" not in encoded
    assert ".env" not in encoded
