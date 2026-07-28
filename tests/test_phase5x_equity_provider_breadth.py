from __future__ import annotations

from lib import equity_provider_breadth as provider


class _Response:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Session:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return _Response(self.payload)


def test_alpha_vantage_overview_normalizes_free_provider_metrics_without_targets(monkeypatch):
    monkeypatch.setattr(provider, "load_runtime_cache_record", lambda key: None)
    saved = []
    monkeypatch.setattr(provider, "save_runtime_cache_record", lambda record: saved.append(record))
    session = _Session(
        {
            "Symbol": "AAPL",
            "Name": "Apple Inc",
            "Exchange": "NASDAQ",
            "Sector": "Technology",
            "Industry": "Consumer Electronics",
            "MarketCapitalization": "3000000000000",
            "PERatio": "28.5",
            "RevenueTTM": "400000000000",
            "ReturnOnEquityTTM": "1.52",
            "AnalystTargetPrice": "9999.99",
        }
    )

    result = provider.fetch_alpha_vantage_overview("AAPL", api_key="unit-key", session=session)

    assert result["availability"] == "available"
    assert result["source_status"] == "live/fresh"
    assert result["metrics"]["alpha_pe_ratio"] == 28.5
    assert result["metrics"]["alpha_return_on_equity"] == 1.52
    assert "AnalystTargetPrice" not in str(result)
    assert "unit-key" not in result["source_url"]
    assert saved


def test_finnhub_company_news_normalizes_source_bound_rows(monkeypatch):
    monkeypatch.setattr(provider, "load_runtime_cache_record", lambda key: None)
    monkeypatch.setattr(provider, "save_runtime_cache_record", lambda record: None)
    session = _Session(
        [
            {
                "headline": "Apple expands services",
                "summary": "Company scoped headline.",
                "datetime": 1782796800,
                "url": "https://example.test/aapl-news",
                "source": "Example Wire",
                "category": "company",
            }
        ]
    )

    result = provider.fetch_finnhub_company_news("AAPL", api_key="unit-key", session=session)

    assert result["availability"] == "available"
    assert result["rows"][0]["provider"] == "Finnhub / Example Wire"
    assert result["rows"][0]["source_status"] == "live/fresh"
    assert result["rows"][0]["exact_symbol_scope"] is True
    assert "unit-key" not in result["source_url"]


def test_missing_optional_keys_are_honest_provider_required(monkeypatch):
    monkeypatch.setattr(provider, "get_env_var", lambda name, default=None: default)

    result = provider.fetch_alpha_vantage_news("AAPL")

    assert result["availability"] == "provider-required"
    assert result["source_status"] == "missing-key"
    assert "ALPHAVANTAGE_API_KEY" in result["data_gap"]


def test_symbol_financial_and_news_context_include_provider_breadth(monkeypatch):
    import lib.symbol_intelligence as module

    identity = {
        "symbol": "AAPL",
        "provider_symbol": "AAPL",
        "asset_class": "equity",
        "name": "Apple Inc.",
        "aliases": ["AAPL", "Apple"],
    }

    def fake_panel_fetch(key, *, runtime_mode, ttl_seconds, provider, source_url, fetcher):
        if "financials" in key:
            return {"metrics": {"market_cap": 1_000_000}, "statements": {}, "sec_identity": None}, "live/fresh", None, "2026-06-30T00:00:00+00:00"
        return {"rows": []}, "live/fresh", None, "2026-06-30T00:00:00+00:00"

    monkeypatch.setattr(module, "_panel_from_cache_or_fetch", fake_panel_fetch)
    monkeypatch.setattr(
        module.equity_provider_breadth,
        "build_equity_provider_breadth",
        lambda identity: {
            "availability": "available",
            "source_status": "live/fresh",
            "metrics": {"alpha_pe_ratio": 28.5},
            "profile": {"finnhub_industry": "Technology"},
            "source_register": [{"provider": "Alpha Vantage", "source": "alpha-vantage-overview", "source_status": "live/fresh", "row_count": 5}],
            "data_gap": None,
        },
    )
    monkeypatch.setattr(
        module.equity_provider_breadth,
        "build_equity_news_context",
        lambda identity: {
            "availability": "available",
            "source_status": "live/fresh",
            "rows": [{"title": "Apple services update", "published_at": "2026-06-30T00:00:00+00:00", "source_url": "https://example.test/aapl", "provider": "Finnhub / Example", "match_terms": ["AAPL"], "exact_symbol_scope": True}],
            "source_register": [{"provider": "Finnhub", "source": "finnhub-company-news", "source_status": "live/fresh", "row_count": 1}],
            "data_gap": None,
        },
    )

    financial = module._financial_context(identity, "live-if-available", "1d", "3mo")
    news = module._exact_news(identity, "live-if-available", "1d", "3mo")

    assert financial["provider_breadth"]["availability"] == "available"
    assert financial["metrics"]["alpha_pe_ratio"] == 28.5
    assert financial["source_register"][0]["provider"] == "Alpha Vantage"
    assert news["rows"][0]["provider"] == "Finnhub / Example"
    assert news["source_status"] == "live/fresh"
