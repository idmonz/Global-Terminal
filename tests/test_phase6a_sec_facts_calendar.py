from __future__ import annotations

import json

from lib import equity_provider_breadth
from lib.sec_edgar_provider import build_sec_company_facts_context, normalize_sec_company_facts


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def _sec_payload():
    return {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "label": "Revenue",
                    "description": "Revenue from contracts with customers.",
                    "units": {
                        "USD": [
                            {
                                "start": "2025-09-28",
                                "end": "2026-06-27",
                                "val": 312_000_000_000,
                                "accn": "0000320193-26-000001",
                                "fy": 2026,
                                "fp": "Q3",
                                "form": "10-Q",
                                "filed": "2026-07-31",
                                "frame": "CY2026Q2",
                            }
                        ],
                        "shares": [
                            {
                                "end": "2026-06-27",
                                "val": 15_000_000_000,
                                "form": "10-Q",
                                "filed": "2026-07-31",
                            }
                        ],
                    },
                },
                "EarningsPerShareDiluted": {
                    "label": "Diluted EPS",
                    "description": "Diluted earnings per share.",
                    "units": {
                        "USD/shares": [
                            {
                                "start": "2025-09-28",
                                "end": "2026-06-27",
                                "val": 6.21,
                                "accn": "0000320193-26-000001",
                                "fy": 2026,
                                "fp": "Q3",
                                "form": "10-Q",
                                "filed": "2026-07-31",
                            }
                        ]
                    },
                },
            }
        },
    }


def test_sec_fact_normalization_preserves_concept_unit_period_form_and_filed_date():
    rows = normalize_sec_company_facts(_sec_payload())

    assert len(rows) == 2
    revenue = next(row for row in rows if row["concept"] == "RevenueFromContractWithCustomerExcludingAssessedTax")
    eps = next(row for row in rows if row["concept"] == "EarningsPerShareDiluted")
    assert revenue["unit"] == "USD"
    assert revenue["value"] == 312_000_000_000
    assert revenue["start"] == "2025-09-28"
    assert revenue["end"] == "2026-06-27"
    assert revenue["form"] == "10-Q"
    assert revenue["filed"] == "2026-07-31"
    assert revenue["accession"] == "0000320193-26-000001"
    assert eps["unit"] == "USD/shares"
    assert eps["value"] == 6.21
    assert not any(row["unit"] == "shares" for row in rows)


def test_sec_company_fact_context_is_source_bound_and_secret_free():
    session = FakeSession(_sec_payload())
    context = build_sec_company_facts_context(
        "0000320193",
        session=session,
        user_agent="Research Terminal contact@example.test",
    )

    assert context["availability"] == "available"
    assert context["source_status"] == "live/fresh"
    assert context["cik"] == "0000320193"
    assert context["entity_name"] == "Apple Inc."
    assert len(context["facts"]) == 2
    assert context["source_register"][0]["provider"] == "sec_edgar"
    encoded = json.dumps(context)
    assert "contact@example.test" not in encoded
    assert "api_key" not in encoded


def test_alpha_vantage_earnings_normalizes_reported_rows_without_zero_fill(monkeypatch):
    monkeypatch.setattr(equity_provider_breadth, "load_runtime_cache_record", lambda key: None)
    monkeypatch.setattr(equity_provider_breadth, "save_runtime_cache_record", lambda record: None)
    session = FakeSession(
        {
            "symbol": "AAPL",
            "quarterlyEarnings": [
                {
                    "fiscalDateEnding": "2026-06-30",
                    "reportedDate": "2026-07-30",
                    "reportedEPS": "1.45",
                    "estimatedEPS": "1.39",
                    "surprise": "0.06",
                    "surprisePercentage": "4.3165",
                },
                {
                    "fiscalDateEnding": "2026-03-31",
                    "reportedDate": "2026-05-01",
                    "reportedEPS": "None",
                    "estimatedEPS": "1.50",
                    "surprise": "None",
                    "surprisePercentage": "None",
                },
            ],
        }
    )

    result = equity_provider_breadth.fetch_alpha_vantage_earnings(
        "AAPL",
        api_key="test-key",
        session=session,
    )

    assert result["availability"] == "available"
    assert result["rows"][0]["event_type"] == "reported-earnings"
    assert result["rows"][0]["reported_eps"] == 1.45
    assert result["rows"][1]["reported_eps"] is None
    assert result["rows"][1]["surprise"] is None
    assert "test-key" not in json.dumps(result)


def test_finnhub_calendar_preserves_date_only_timezone_uncertainty(monkeypatch):
    monkeypatch.setattr(equity_provider_breadth, "load_runtime_cache_record", lambda key: None)
    monkeypatch.setattr(equity_provider_breadth, "save_runtime_cache_record", lambda record: None)
    session = FakeSession(
        {
            "earningsCalendar": [
                {
                    "date": "2026-07-30",
                    "symbol": "AAPL",
                    "hour": "amc",
                    "quarter": 3,
                    "year": 2026,
                    "epsEstimate": 1.39,
                    "epsActual": None,
                    "revenueEstimate": 90_000_000_000,
                    "revenueActual": None,
                }
            ]
        }
    )

    result = equity_provider_breadth.fetch_finnhub_earnings_calendar(
        "AAPL",
        api_key="test-key",
        session=session,
        today="2026-07-01",
    )

    row = result["rows"][0]
    assert row["event_type"] == "scheduled-earnings"
    assert row["event_date"] == "2026-07-30"
    assert row["event_time_code"] == "amc"
    assert row["timezone"] == "provider-date/timezone-unspecified"
    assert row["reported_eps"] is None
    assert row["revenue_actual"] is None


def test_combined_earnings_context_reports_missing_keys_honestly(monkeypatch):
    monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    identity = {"symbol": "AAPL", "provider_symbol": "AAPL", "asset_class": "equity"}

    result = equity_provider_breadth.build_equity_earnings_context(identity)

    assert result["availability"] == "provider-required"
    assert result["rows"] == []
    assert {row["source_status"] for row in result["provider_rows"]} == {"missing-key"}
    assert "target" not in json.dumps(result).lower()


def test_symbol_financial_context_carries_sec_facts_and_earnings(monkeypatch):
    from lib import symbol_intelligence as module

    identity = {
        "symbol": "AAPL",
        "provider_symbol": "AAPL",
        "asset_class": "equity",
    }
    sec_context = {
        "availability": "available",
        "source_status": "cached",
        "facts": [{"concept": "Assets", "unit": "USD", "value": 100, "form": "10-Q", "filed": "2026-07-31"}],
        "source_register": [{"provider": "sec_edgar", "source_status": "cached", "row_count": 1}],
    }
    monkeypatch.setattr(
        module,
        "_panel_from_cache_or_fetch",
        lambda *args, **kwargs: (
            {"metrics": {"market_cap": 1_000}, "statements": {}, "sec_identity": {"cik": "0000320193"}, "sec_facts": sec_context},
            "cached",
            None,
            "2026-07-01T00:00:00+00:00",
        ),
    )
    monkeypatch.setattr(
        module.equity_provider_breadth,
        "build_equity_provider_breadth",
        lambda identity: {"availability": "available", "metrics": {}, "source_register": [], "data_gap": None},
    )
    monkeypatch.setattr(
        module.equity_provider_breadth,
        "build_equity_earnings_context",
        lambda identity: {
            "availability": "available",
            "source_status": "cached",
            "rows": [{"event_type": "scheduled-earnings", "event_date": "2026-07-30"}],
            "source_register": [{"provider": "Finnhub", "source_status": "cached", "row_count": 1}],
            "data_gap": None,
        },
    )

    result = module._financial_context(identity, "live-if-available", "1d", "3mo")

    assert result["sec_facts"]["facts"][0]["concept"] == "Assets"
    assert result["earnings_calendar"]["rows"][0]["event_type"] == "scheduled-earnings"
    assert {row["provider"] for row in result["source_register"]} == {"sec_edgar", "Finnhub"}
