from __future__ import annotations

from lib.provider_diagnostics import (
    provider_gap_report,
    provider_health_summary,
    test_all_configured_providers as run_all_configured_providers,
    test_provider_connection as run_provider_connection,
)


def test_provider_diagnostics_missing_keys_and_mock_probe(monkeypatch):
    monkeypatch.delenv("AISSTREAM_API_KEY", raising=False)
    missing = run_provider_connection("aisstream")
    assert missing["status"] == "missing_key"
    assert missing["requires_key"]

    ok = run_provider_connection("yfinance", requester=lambda provider: {"ok": True})
    assert ok["status"] == "ok"
    assert ok["latency_ms"] >= 0

    summary = provider_health_summary()
    assert summary["total_providers"] >= summary["available"]
    assert "paid providers are not required" in summary["caveat"]
    assert not provider_gap_report().empty
    assert not run_all_configured_providers(requester=lambda provider: {"ok": True}).empty
