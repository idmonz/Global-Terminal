from __future__ import annotations

import json

import pandas as pd

import lib.portfolio_risk_workstation as workspace
from backend.api.app import get_portfolio_risk_payload
from lib.api_contracts import validate_api_payload
from lib.data_status import success
from lib.portfolio_risk_workstation import (
    build_demo_portfolio_holdings,
    build_portfolio_risk_workstation_contract,
    normalize_holdings,
    reset_portfolio_risk_cache,
)


def _history(start: str, values: list[float]) -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(values), freq="B")
    return pd.DataFrame(
        {
            "date": dates,
            "open": values,
            "high": [value * 1.01 for value in values],
            "low": [value * 0.99 for value in values],
            "close": values,
            "adj_close": values,
            "volume": [1_000_000.0] * len(values),
        }
    )


def test_demo_contract_is_useful_reconciled_and_privacy_labeled():
    payload = build_portfolio_risk_workstation_contract(include_runtime=False)

    assert payload["portfolio_risk_version"] == "portfolio_risk.v1"
    assert payload["summary"]["source_status"] == "fixture"
    assert payload["summary"]["holding_count"] >= 6
    assert payload["summary"]["total_market_value"] > 0
    assert payload["summary"]["valuation_coverage_pct"] == 100.0
    assert len(payload["performance"]["series"]) >= 200
    assert payload["performance"]["methods"]["time_weighted"]["available"] is True
    assert payload["performance"]["methods"]["money_weighted"]["available"] is False
    assert payload["risk"]["sample_count"] >= 200
    assert len(payload["correlation"]["matrix"]) >= 4
    assert payload["factors"]["model"] == "public_proxy_ols"
    assert payload["attribution"]["reconciled"] is True
    assert len(payload["stress_tests"]) >= 8
    assert payload["privacy"]["classification"] == "deterministic_fictional_demo"
    assert payload["privacy"]["release_safe"] is True
    assert payload["research_snapshot"]["guard_summary"]["guard_count"] > 0
    assert payload["research_snapshot"]["quantities_in_snapshot"] is False
    assert payload["research_snapshot"]["cost_basis_in_snapshot"] is False
    assert payload["readiness"]["missing_returns_as_zero"] is False
    assert payload["readiness"]["broker_execution_added"] is False
    assert all(row["not_financial_advice"] is True for row in payload["holdings"])


def test_normalization_rejects_duplicate_nonpositive_and_non_usd_without_fx():
    normalized = normalize_holdings(
        [
            {"symbol": "AAPL", "quantity": 3, "cost_basis": 100, "currency": "USD"},
            {"symbol": "aapl", "quantity": 2, "cost_basis": 110, "currency": "USD"},
            {"symbol": "MSFT", "quantity": 0, "cost_basis": 50, "currency": "USD"},
            {"symbol": "EWJ", "quantity": 1, "cost_basis": 60, "currency": "JPY"},
        ]
    )

    assert normalized["valid"] is False
    assert len(normalized["accepted_rows"]) == 1
    reasons = {reason for row in normalized["rejected_rows"] for reason in row["reasons"]}
    assert "duplicate_symbol" in reasons
    assert "non_positive_quantity" in reasons
    assert "fx_rate_required" in reasons


def test_runtime_uses_complete_overlap_and_missing_symbol_is_not_zero(monkeypatch):
    holdings = [
        {"symbol": "AAPL", "name": "Apple", "asset_class": "stock", "sector": "Technology", "quantity": 10, "cost_basis": 100, "currency": "USD"},
        {"symbol": "MISS", "name": "Missing", "asset_class": "stock", "sector": "Other", "quantity": 5, "cost_basis": 50, "currency": "USD"},
        {"symbol": "CASH", "name": "Cash", "asset_class": "cash", "sector": "Cash", "quantity": 1000, "cost_basis": 1, "currency": "USD"},
    ]
    aapl = [100 + index * 0.2 for index in range(100)]
    spy = [200 + index * 0.1 for index in range(100)]

    def fake_fetch(symbols, *, period):
        data = {"AAPL": _history("2025-01-02", aapl), "SPY": _history("2025-01-02", spy)}
        return {symbol: data[symbol] for symbol in symbols if symbol in data}, success(
            data,
            source="AAPL,MISS,SPY",
            provider="test-provider",
            coverage="2/3 tickers",
        )

    monkeypatch.setattr(workspace, "fetch_many_price_histories", fake_fetch)
    reset_portfolio_risk_cache()
    payload = build_portfolio_risk_workstation_contract(
        portfolio_id="local-safe",
        holdings=holdings,
        include_runtime=True,
    )

    missing = next(row for row in payload["holdings"] if row["symbol"] == "MISS")
    assert missing["price"] is None
    assert missing["market_value"] is None
    assert missing["history_available"] is False
    assert payload["summary"]["valuation_coverage_pct"] < 100
    assert payload["summary"]["history_coverage_pct"] < 100
    assert payload["readiness"]["missing_returns_as_zero"] is False
    assert "MISS" in payload["summary"]["missing_symbols"]
    assert payload["performance"]["sample_count"] == 99


def test_provider_failure_never_claims_live_or_fabricates_performance(monkeypatch):
    def fail_fetch(symbols, *, period):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(workspace, "fetch_many_price_histories", fail_fetch)
    reset_portfolio_risk_cache()
    payload = build_portfolio_risk_workstation_contract(include_runtime=True)

    assert payload["summary"]["source_status"] == "unavailable"
    assert payload["performance"]["available"] is False
    assert payload["performance"]["series"] == []
    assert payload["data_gaps"]
    assert payload["readiness"]["live_portfolio_claimed"] is False


def test_runtime_refresh_failure_uses_explicit_stale_history(monkeypatch):
    clock = {"value": 1000.0}
    calls = {"count": 0}
    values = [100 + index * 0.15 for index in range(100)]

    def fake_fetch(symbols, *, period):
        calls["count"] += 1
        if calls["count"] > 1:
            raise RuntimeError("refresh failed")
        data = {symbol: _history("2025-01-02", values) for symbol in symbols}
        return data, success(data, source=",".join(symbols), provider="test-provider", coverage="all")

    monkeypatch.setattr(workspace, "fetch_many_price_histories", fake_fetch)
    monkeypatch.setattr(workspace.time, "monotonic", lambda: clock["value"])
    reset_portfolio_risk_cache()
    first = build_portfolio_risk_workstation_contract(include_runtime=True)
    clock["value"] += workspace.PORTFOLIO_CACHE_TTL_SECONDS + 1
    stale = build_portfolio_risk_workstation_contract(include_runtime=True)

    assert first["summary"]["source_status"] == "live/fresh"
    assert stale["summary"]["source_status"] == "stale"
    assert stale["performance"]["available"] is True
    assert "refresh failed" in " ".join(stale["data_gaps"])


def test_pairwise_counts_and_contributions_reconcile_without_null_coercion():
    payload = build_portfolio_risk_workstation_contract(include_runtime=False)
    assets = payload["correlation"]["assets"]
    counts = payload["correlation"]["pairwise_sample_counts"]
    assert len(counts) == len(assets)
    assert all(len(row) == len(assets) for row in counts)
    assert min(min(row) for row in counts) >= 20
    risk_total = sum(row["risk_contribution"] for row in payload["attribution"]["risk_contribution"])
    assert abs(risk_total - 1.0) < 1e-6
    return_total = sum(row["return_contribution"] for row in payload["attribution"]["return_contribution"])
    assert abs(return_total + payload["attribution"]["residual"] - payload["attribution"]["portfolio_total_return"]) < 1e-9


def test_api_envelope_and_fixture_are_json_safe_and_private_path_free():
    payload = get_portfolio_risk_payload(
        portfolio_id="demo-core",
        period="1y",
        benchmark="SPY",
        include_runtime=False,
    )
    valid, issues = validate_api_payload(payload)
    assert valid, issues
    assert payload["payload_type"] == "portfolio_risk"
    assert payload["data"]["portfolio_risk_version"] == "portfolio_risk.v1"
    encoded = json.dumps(payload, sort_keys=True)
    assert "data/private" not in encoded
    assert ".env" not in encoded
    assert "account_id" not in encoded
    assert "sk-" not in encoded


def test_demo_holdings_are_deterministic_fictional_research_rows():
    first = build_demo_portfolio_holdings()
    second = build_demo_portfolio_holdings()
    assert first == second
    assert all(row["input_classification"] == "deterministic_fictional_demo" for row in first)
    assert all(row["quantity"] > 0 for row in first)
