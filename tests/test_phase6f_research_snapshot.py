from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import lib.runtime_cache as runtime_cache
from lib.research_snapshot import (
    RESEARCH_SNAPSHOT_VERSION,
    build_research_snapshot_rows,
    default_provider_budget,
)
from lib.runtime_cache import RuntimeCacheRecord, save_runtime_cache_record
from lib.symbol_intelligence import build_symbol_delivery_contract
from lib.symbol_workstation import history_cache_key, resolve_symbol
from lib.watchlist_desk import (
    add_watchlist_symbol,
    build_watchlist_desk_contract,
    create_watchlist,
    materialize_watchlist,
)


PRIVATE_REASON = "phase6f-private-thesis-must-never-leak"
NOW = datetime(2026, 7, 3, 2, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _isolated_runtime_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_cache, "RUNTIME_CACHE_DIR", tmp_path / "runtime-cache")
    runtime_cache.clear_runtime_cache()
    yield
    runtime_cache.clear_runtime_cache()


def _identities() -> list[dict]:
    identities = [
        resolve_symbol(symbol, asset_class="equity", include_materialized=False)
        for symbol in ("AAPL", "TSLA", "JNJ", "TTE", "TMUS")
    ]
    assert all(isinstance(identity, dict) for identity in identities)
    return [dict(identity) for identity in identities if identity is not None]


def _history(seed: float) -> list[dict]:
    return [
        {
            "date": f"2026-{4 + index // 28:02d}-{1 + index % 28:02d}",
            "open": seed + index - 0.5,
            "high": seed + index + 1,
            "low": seed + index - 1,
            "close": seed + index,
            "volume": 1_000_000 + index * 1_000,
        }
        for index in range(70)
    ]


def _available_overview(symbol: str) -> dict:
    return {
        "availability": "available",
        "provider": "Alpha Vantage",
        "source": "alpha-vantage-overview",
        "source_url": "https://www.alphavantage.co/query",
        "source_status": "live/fresh",
        "fetched_at": NOW.isoformat(),
        "metrics": {
            "alpha_market_cap": 3_000_000_000_000,
            "alpha_revenue_ttm": 400_000_000_000,
            "alpha_eps": 7.1,
            "alpha_pe_ratio": 31.5,
            "alpha_annual_dividend_per_share": 1.04,
            "alpha_dividend_yield": 0.004,
        },
        "profile": {
            "alpha_name": symbol,
            "alpha_dividend_date": "2026-08-13",
            "alpha_ex_dividend_date": "2026-08-10",
        },
        "data_gap": None,
        "caveat": "Supplemental fundamentals.",
        "not_financial_advice": True,
    }


def _available_earnings(symbol: str) -> dict:
    return {
        "availability": "available",
        "provider": "Finnhub",
        "source": "finnhub-earnings-calendar",
        "source_url": "https://finnhub.io/api/v1/calendar/earnings",
        "source_status": "live/fresh",
        "fetched_at": NOW.isoformat(),
        "rows": [
            {
                "symbol": symbol,
                "event_type": "scheduled-earnings",
                "event_date": "2026-07-29",
                "estimated_eps": 1.42,
                "reported_eps": None,
                "provider": "Finnhub",
                "source_url": "https://finnhub.io/api/v1/calendar/earnings",
                "source_status": "live/fresh",
                "fetched_at": NOW.isoformat(),
            }
        ],
        "data_gap": None,
        "caveat": "Provider date can change.",
        "not_financial_advice": True,
    }


def _available_news(symbol: str) -> dict:
    return {
        "availability": "available",
        "provider": "Finnhub",
        "source": "finnhub-company-news",
        "source_url": "https://finnhub.io/api/v1/company-news",
        "source_status": "live/fresh",
        "fetched_at": NOW.isoformat(),
        "rows": [
            {
                "title": f"{symbol} files a company update",
                "summary": "Company-scoped provider headline.",
                "published_at": "2026-07-03T01:00:00+00:00",
                "source_url": f"https://example.com/{symbol.lower()}",
                "provider": "Finnhub / Example Wire",
                "source_status": "live/fresh",
                "fetched_at": NOW.isoformat(),
                "exact_symbol_scope": True,
                "match_terms": [symbol],
            }
        ],
        "data_gap": None,
        "caveat": "Verify at the linked publisher.",
        "not_financial_advice": True,
    }


def test_default_budget_is_bounded_for_five_symbols():
    budget = default_provider_budget(max_symbols=5)

    assert budget["maximum_symbols"] == 5
    assert budget["maximum_calls"] == 16
    assert budget["planned_calls"] == {
        "yfinance:multi-history": 1,
        "alpha-vantage:overview": 5,
        "finnhub:earnings-calendar": 5,
        "finnhub:company-news": 5,
    }


def test_snapshot_enriches_five_rows_with_strict_catalyst_evidence_and_call_ledger():
    identities = _identities()
    histories = {
        identity["symbol"]: _history(100.0 + index * 10)
        for index, identity in enumerate(identities)
    }

    result = build_research_snapshot_rows(
        identities,
        histories,
        overview_fetcher=_available_overview,
        earnings_fetcher=_available_earnings,
        news_fetcher=_available_news,
        history_call_count=1,
        now=NOW,
    )

    assert len(result["rows"]) == 5
    assert result["provider_budget"]["actual_calls"] == 16
    assert result["provider_budget"]["actual_calls"] <= result["provider_budget"]["maximum_calls"]
    assert result["summary"]["enriched_count"] == 5
    for row in result["rows"]:
        assert row["research_snapshot_version"] == RESEARCH_SNAPSHOT_VERSION
        assert row["quote"]["last_price"] is not None
        assert row["performance"]["return_1m_pct"] is not None
        assert row["financials"]["metrics"]["market_cap"] is not None
        assert row["catalysts"]["earnings"][0]["symbol"] == row["symbol"]
        assert row["catalysts"]["news"][0]["match_evidence"] == {
            "symbol": row["symbol"],
            "scope": "provider-company-news",
            "exact": True,
            "terms": [row["symbol"]],
        }
        assert row["catalysts"]["dividends"][0]["event_type"] == "dividend"


def test_provider_failure_retains_public_last_known_good_as_stale_without_private_text():
    identity = _identities()[0]
    prior = build_research_snapshot_rows(
        [identity],
        {identity["symbol"]: _history(100)},
        overview_fetcher=_available_overview,
        earnings_fetcher=_available_earnings,
        news_fetcher=_available_news,
        history_call_count=1,
        now=NOW,
    )["rows"][0]

    def failed(provider: str):
        return {
            "availability": "unavailable",
            "provider": provider,
            "source_status": "rate-limited",
            "fetched_at": NOW.isoformat(),
            "metrics": {},
            "rows": [],
            "data_gap": "429 rate limited",
            "caveat": "Refresh failed.",
            "not_financial_advice": True,
        }

    result = build_research_snapshot_rows(
        [identity],
        {identity["symbol"]: _history(101)},
        overview_fetcher=lambda symbol: failed("Alpha Vantage"),
        earnings_fetcher=lambda symbol: failed("Finnhub"),
        news_fetcher=lambda symbol: failed("Finnhub"),
        previous_rows={identity["symbol"]: {**prior, "private_reason": PRIVATE_REASON}},
        history_call_count=1,
        now=NOW,
    )
    row = result["rows"][0]
    encoded = json.dumps(result)

    assert row["financials"]["source_status"] == "stale"
    assert row["catalysts"]["source_status"] == "stale"
    assert result["provider_budget"]["stale_hits"] >= 2
    assert "429 rate limited" in row["data_gap"]
    assert PRIVATE_REASON not in encoded
    assert "private_reason" not in encoded


def test_catalyst_delivery_reads_only_the_exact_cached_snapshot():
    row = build_research_snapshot_rows(
        [_identities()[0]],
        {"AAPL": _history(100)},
        overview_fetcher=_available_overview,
        earnings_fetcher=_available_earnings,
        news_fetcher=_available_news,
        history_call_count=1,
        now=NOW,
    )["rows"][0]
    save_runtime_cache_record(
        RuntimeCacheRecord(
            key="phase6f:research-snapshot:equity:AAPL",
            data=row,
            source="AAPL",
            provider="watchlist-research-snapshot",
            source_url="https://www.alphavantage.co/documentation/",
            fetched_at=NOW,
        )
    )

    payload = build_symbol_delivery_contract(
        "AAPL",
        asset_class="equity",
        runtime_mode="cache",
        delivery="catalysts",
    )
    workstation = payload["workstations"][0]

    assert payload["delivery"]["requested_panel"] == "catalysts"
    assert workstation["identity"]["symbol"] == "AAPL"
    assert workstation["catalyst_context"]["symbol"] == "AAPL"
    assert workstation["catalyst_context"]["news"][0]["match_evidence"]["exact"] is True
    assert workstation["financial_context"]["availability"] == "not-loaded"
    assert workstation["exact_news"]["availability"] == "not-loaded"


def test_fixture_catalyst_panel_never_mixes_provider_cache():
    row = build_research_snapshot_rows(
        [_identities()[0]],
        {"AAPL": _history(100)},
        overview_fetcher=_available_overview,
        earnings_fetcher=_available_earnings,
        news_fetcher=_available_news,
        history_call_count=1,
        now=NOW,
    )["rows"][0]
    save_runtime_cache_record(
        RuntimeCacheRecord(
            key="phase6f:research-snapshot:equity:AAPL",
            data=row,
            source="AAPL",
            provider="watchlist-research-snapshot",
            source_url="https://www.alphavantage.co/documentation/",
            fetched_at=NOW,
        )
    )

    payload = build_symbol_delivery_contract(
        "AAPL",
        asset_class="equity",
        runtime_mode="fixture",
        delivery="catalysts",
    )
    catalysts = payload["workstations"][0]["catalyst_context"]

    assert catalysts["availability"] == "fixture-unavailable"
    assert catalysts["source_status"] == "fixture"
    assert catalysts["earnings"] == []
    assert catalysts["news"] == []


def test_watchlist_materialization_persists_budgeted_research_rows(tmp_path, monkeypatch):
    import lib.watchlist_desk as desk

    db = tmp_path / "phase6f.db"
    create_watchlist("Catalyst Radar", list_id="catalyst-radar", db_path=db)
    for identity in _identities():
        add_watchlist_symbol(
            "catalyst-radar",
            identity["symbol"],
            asset_class="equity",
            private_reason=PRIVATE_REASON,
            db_path=db,
        )

    def fake_prime(identities, *, interval, range_name):
        rows = []
        for index, identity in enumerate(identities):
            history = _history(100 + index * 10)
            save_runtime_cache_record(
                RuntimeCacheRecord(
                    key=history_cache_key(identity["asset_class"], identity["symbol"], interval, range_name),
                    data=history,
                    source=identity["symbol"],
                    provider="yfinance",
                    source_url=f"https://finance.yahoo.com/quote/{identity['symbol']}",
                    fetched_at=NOW,
                )
            )
            rows.append(
                {
                    "symbol": identity["symbol"],
                    "status": "fresh",
                    "source_status": "live/fresh",
                    "history_row_count": len(history),
                    "fetched_at": NOW.isoformat(),
                    "data_gap": None,
                }
            )
        return {"rows": rows, "provider_call_count": 1}

    monkeypatch.setattr(desk, "_prime_history_batch", fake_prime)
    monkeypatch.setattr(desk, "fetch_alpha_vantage_overview", _available_overview)
    monkeypatch.setattr(desk, "fetch_finnhub_earnings_calendar", _available_earnings)
    monkeypatch.setattr(desk, "fetch_finnhub_company_news", _available_news)

    job = materialize_watchlist(
        "catalyst-radar",
        max_symbols=5,
        db_path=db,
    )
    contract = build_watchlist_desk_contract(
        list_id="catalyst-radar",
        selected_symbol="TSLA",
        db_path=db,
    )
    encoded = json.dumps(contract)

    assert job["provider_call_budget"] == 16
    assert job["provider_call_count"] == 16
    assert job["provider_budget"]["actual_calls_by_operation"]["alpha-vantage:overview"] == 5
    assert job["provider_budget"]["actual_calls_by_operation"]["finnhub:company-news"] == 5
    assert len(job["rows"]) == 5
    assert contract["summary"]["research_enriched_count"] == 5
    assert contract["selected"]["symbol"] == "TSLA"
    assert contract["selected"]["advanced"]["market_cap"] is not None
    assert contract["selected"]["catalysts"]["next_event"] is not None
    assert PRIVATE_REASON not in encoded
    assert contract["privacy"]["private_reason_in_payload"] is False


def test_catalyst_http_panel_is_etagged_and_unknown_identity_isolated():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api.app import create_app

    row = build_research_snapshot_rows(
        [_identities()[0]],
        {"AAPL": _history(100)},
        overview_fetcher=_available_overview,
        earnings_fetcher=_available_earnings,
        news_fetcher=_available_news,
        history_call_count=1,
        now=NOW,
    )["rows"][0]
    save_runtime_cache_record(
        RuntimeCacheRecord(
            key="phase6f:research-snapshot:equity:AAPL",
            data=row,
            source="AAPL",
            provider="watchlist-research-snapshot",
            source_url="https://www.alphavantage.co/documentation/",
            fetched_at=NOW,
        )
    )
    client = TestClient(create_app())
    response = client.get(
        "/api/symbol-workstation/AAPL/panels/catalysts",
        params={"asset_class": "equity", "runtime_mode": "cache"},
    )

    assert response.status_code == 200
    assert response.headers["etag"]
    assert response.json()["data"]["workstations"][0]["catalyst_context"]["symbol"] == "AAPL"
    conditional = client.get(
        "/api/symbol-workstation/AAPL/panels/catalysts",
        params={"asset_class": "equity", "runtime_mode": "cache"},
        headers={"If-None-Match": response.headers["etag"]},
    )
    assert conditional.status_code == 304

    unknown = client.get(
        "/api/symbol-workstation/NOTAREAL123/panels/catalysts",
        params={"asset_class": "equity", "runtime_mode": "cache"},
    )
    assert unknown.status_code == 404
    assert "AAPL" not in unknown.text


def test_phase6f_frontend_exposes_saved_catalysts_and_url_state_without_row_fanout():
    root = Path(__file__).resolve().parents[1]
    watchlist = (root / "apps/web/src/components/WatchlistDesk.tsx").read_text(encoding="utf-8")
    progressive = (root / "apps/web/src/components/ProgressiveSymbolWorkstation.tsx").read_text(encoding="utf-8")

    assert 'key: "catalysts"' in watchlist
    assert 'data-provider-fanout="false"' in watchlist
    assert 'next.searchParams.set("watchMode"' in watchlist
    assert 'next.searchParams.set("sort"' in watchlist
    assert 'next.searchParams.set("group"' in watchlist
    assert 'next.searchParams.set("panel"' in watchlist
    assert "Saved snapshot / 0 request-time provider calls" in watchlist
    assert 'deskMode === "fixture" ? "cache" : runtimeMode' in watchlist
    assert 'panel: "catalysts"' in progressive
    assert "data-progressive-catalyst-count" in progressive
