from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import lib.options_quant_workstation as workspace
from backend.api.app import get_options_quant_payload
from lib.options_quant_workstation import (
    build_options_quant_workstation_contract,
    normalize_provider_option_rows,
    reset_options_quant_cache,
)


@dataclass
class FakeStatus:
    ok: bool = True
    provider: str = "yfinance options"
    error: str | None = None

    def to_dict(self):
        return {
            "status": "fresh" if self.ok else "unavailable",
            "provider": self.provider,
            "error": self.error,
            "fetched_at": "2026-06-21T00:00:00+00:00",
        }


def _frame(side: str, expiry: str, *, crossed: bool = False, missing_oi: bool = False):
    return pd.DataFrame(
        [
            {
                "contractSymbol": f"AAPL{expiry.replace('-', '')}{side[0].upper()}00200000",
                "lastTradeDate": "2026-06-20T19:30:00+00:00",
                "strike": 200.0,
                "lastPrice": 5.2,
                "bid": 6.0 if crossed else 5.0,
                "ask": 5.5,
                "volume": 120,
                "openInterest": None if missing_oi else 900,
                "impliedVolatility": 0.24,
                "inTheMoney": False,
                "contractSize": "REGULAR",
                "currency": "USD",
            }
        ]
    )


def test_fixture_contract_is_useful_and_assumption_labeled():
    payload = build_options_quant_workstation_contract(symbol="AAPL", include_runtime=False)

    assert payload["options_quant_version"] == "options_quant.v2"
    assert len(payload["expiries"]) >= 3
    assert len(payload["chain_rows"]) >= 30
    assert payload["summary"]["source_status"] == "fixture"
    assert payload["readiness"]["surface_ready"] is True
    assert payload["readiness"]["gex_ready"] is True
    assert payload["assumptions"]["dealer_sign_convention"]["observed_dealer_positioning"] is False
    assert all(row["not_financial_advice"] is True for row in payload["chain_rows"])


def test_provider_normalizer_rejects_crossed_market_and_preserves_missing_oi():
    expiry = "2030-01-18"
    calls = pd.concat([_frame("call", expiry, missing_oi=True), _frame("call", expiry, crossed=True)], ignore_index=True)
    puts = _frame("put", expiry)

    normalized = normalize_provider_option_rows(
        symbol="AAPL",
        expiry=expiry,
        calls=calls,
        puts=puts,
        underlying_price=200.0,
        fetched_at="2026-06-21T00:00:00+00:00",
        source_status="live/fresh",
    )

    assert len(normalized["rows"]) == 2
    assert len(normalized["rejected_rows"]) == 1
    call = next(row for row in normalized["rows"] if row["option_type"] == "call")
    assert call["open_interest"] is None
    assert "missing_open_interest" in call["quality_flags"]
    assert "bid_greater_than_ask" in normalized["rejected_rows"][0]["reasons"]
    assert "duplicate_contract_identity" in normalized["rejected_rows"][0]["reasons"]


def test_runtime_contract_uses_provider_rows_and_provenance(monkeypatch):
    reset_options_quant_cache()
    expiries = ["2030-01-18", "2030-02-15"]
    monkeypatch.setattr(workspace, "get_options_expirations", lambda symbol: (expiries, FakeStatus()))
    monkeypatch.setattr(
        workspace,
        "get_options_chain",
        lambda symbol, expiry=None: (
            {
                "calls": _frame("call", expiry or expiries[0]),
                "puts": _frame("put", expiry or expiries[0]),
                "expiry": expiry or expiries[0],
                "underlying_price": 200.0,
            },
            FakeStatus(),
        ),
    )

    payload = build_options_quant_workstation_contract(symbol="AAPL", expiry=expiries[0], include_runtime=True)

    assert payload["summary"]["source_status"] == "live/fresh"
    assert payload["summary"]["chain_row_count"] == 4
    assert payload["readiness"]["live_option_chain_claimed"] is True
    assert {row["provider"] for row in payload["chain_rows"]} == {"yfinance options"}
    assert all(row["source_url"].startswith("https://finance.yahoo.com/quote/AAPL") for row in payload["chain_rows"])
    assert all(row["fetched_at"] for row in payload["chain_rows"])


def test_provider_failure_is_explicit_and_never_fake_live(monkeypatch):
    reset_options_quant_cache()
    monkeypatch.setattr(
        workspace,
        "get_options_expirations",
        lambda symbol: ([], FakeStatus(ok=False, error="provider unavailable")),
    )

    payload = build_options_quant_workstation_contract(symbol="AAPL", include_runtime=True)

    assert payload["chain_rows"] == []
    assert payload["summary"]["source_status"] == "unavailable"
    assert payload["readiness"]["live_option_chain_claimed"] is False
    assert payload["unavailable_sources"]
    assert "provider unavailable" in payload["unavailable_sources"][0]["data_gap"]


def test_runtime_cache_and_stale_fallback(monkeypatch):
    reset_options_quant_cache()
    expiry = "2030-01-18"
    calls = {"count": 0}
    monkeypatch.setattr(workspace, "get_options_expirations", lambda symbol: ([expiry], FakeStatus()))

    def fetch(symbol, expiry=None):
        calls["count"] += 1
        return (
            {"calls": _frame("call", expiry), "puts": _frame("put", expiry), "expiry": expiry, "underlying_price": 200.0},
            FakeStatus(),
        )

    monkeypatch.setattr(workspace, "get_options_chain", fetch)
    first = build_options_quant_workstation_contract(symbol="AAPL", include_runtime=True)
    second = build_options_quant_workstation_contract(symbol="AAPL", include_runtime=True)
    assert first["summary"]["source_status"] == "live/fresh"
    assert second["summary"]["source_status"] == "cached"
    assert calls["count"] == 1

    monkeypatch.setattr(workspace, "_CACHE_TTL_SECONDS", -1)
    monkeypatch.setattr(
        workspace,
        "get_options_expirations",
        lambda symbol: ([], FakeStatus(ok=False, error="refresh failed")),
    )
    stale = build_options_quant_workstation_contract(symbol="AAPL", include_runtime=True)
    assert stale["summary"]["source_status"] == "stale"
    assert "refresh failed" in " ".join(stale["data_gaps"])


def test_api_route_accepts_expiry_and_returns_v2_fixture():
    payload = get_options_quant_payload(symbol="AAPL", expiry="2030-01-18", include_runtime=False)
    assert payload["payload_type"] == "options_quant"
    assert payload["data"]["options_quant_version"] == "options_quant.v2"
    assert payload["data"]["selected_expiry"] == "2030-01-18"


def test_web_contract_has_product_first_options_markers():
    root = Path(__file__).resolve().parents[1]
    page = (root / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    component = (root / "apps/web/src/components/OptionsQuantWorkstation.tsx").read_text(encoding="utf-8")
    css = (root / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    assert 'requestedView === "options-quant"' in page
    assert 'data-product-view="options-quant-workstation"' in page
    for marker in ["surface", "expiry", "optionType", "moneyness", "selected", "compare"]:
        assert marker in component
    assert "options-chain-table" in component
    assert "options-iv-chart" in component
    assert "options-scenario-matrix" in component
    assert ".options-product-shell" in css
