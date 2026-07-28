from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib.api_contracts import validate_api_payload
from lib.symbol_intelligence import build_symbol_delivery_contract
from lib.watchlist_desk import compute_watchlist_advanced_metrics


ROOT = Path(__file__).resolve().parents[1]


def _history(count: int = 90) -> list[dict[str, object]]:
    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        close = 100.0 + index * 0.5 + (index % 7) * 0.2
        rows.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "open": close - 0.4,
                "high": close + 0.8,
                "low": close - 0.9,
                "close": close,
                "adj_close": close,
                "volume": 1_000_000 + index * 1_000,
            }
        )
    return rows


def test_compact_chart_core_is_exact_source_backed_and_materially_smaller():
    full = build_symbol_delivery_contract(
        "AAPL",
        asset_class="equity",
        runtime_mode="fixture",
        delivery="chart",
    )
    compact = build_symbol_delivery_contract(
        "AAPL",
        asset_class="equity",
        runtime_mode="fixture",
        delivery="chart-core",
    )

    full_bytes = len(json.dumps(full, separators=(",", ":")))
    compact_bytes = len(json.dumps(compact, separators=(",", ":")))
    workstation = compact["workstations"][0]
    price = workstation["chart_views"]["price"]

    assert workstation["identity"]["symbol"] == "AAPL"
    assert workstation["history"] == []
    assert price["candles"]
    assert price["volume"]
    assert price["provider"]
    assert price["source_status"]
    assert workstation["financial_context"]["availability"] == "not-loaded"
    assert workstation["exact_news"]["availability"] == "not-loaded"
    assert compact_bytes < full_bytes * 0.5
    assert compact["delivery"]["provider_refresh_allowed"] is False
    ok, issues = validate_api_payload(
        {
            "contract_version": "phase_2b.v1",
            "payload_type": "test",
            "generated_at": "2026-07-02T00:00:00+00:00",
            "data": compact,
            "source_status": compact["source_register"],
            "summary": compact["summary"],
            "caveats": [],
        }
    )
    assert ok, issues


def test_technicals_delivery_is_panel_scoped_and_has_no_financial_or_news(monkeypatch):
    import lib.symbol_intelligence as intelligence

    monkeypatch.setattr(
        intelligence,
        "_financial_context",
        lambda *args, **kwargs: pytest.fail("technicals must not load financials"),
    )
    monkeypatch.setattr(
        intelligence,
        "_exact_news",
        lambda *args, **kwargs: pytest.fail("technicals must not load news"),
    )
    payload = build_symbol_delivery_contract(
        "TSLA",
        asset_class="equity",
        runtime_mode="fixture",
        delivery="technicals",
    )
    workstation = payload["workstations"][0]

    assert workstation["identity"]["symbol"] == "TSLA"
    assert workstation["technical_analysis"]["status"] in {"available", "partial"}
    assert workstation["chart_views"]["price"] == {}
    assert workstation["history"] == []
    assert workstation["financial_context"]["availability"] == "not-loaded"
    assert workstation["exact_news"]["availability"] == "not-loaded"


def test_watchlist_advanced_metrics_are_deterministic_cache_derivatives():
    metrics = compute_watchlist_advanced_metrics(_history())

    assert metrics["status"] == "available"
    assert metrics["observation_count"] == 90
    assert metrics["return_1w_pct"] is not None
    assert metrics["return_1m_pct"] is not None
    assert metrics["return_3m_pct"] is not None
    assert metrics["realized_volatility_1m_pct"] is not None
    assert metrics["rsi_14"] is not None
    assert metrics["trend_state"] in {"bullish", "bearish", "mixed"}
    assert metrics["provider_calls"] == 0
    assert metrics["calculation_source"] == "existing-symbol-history-cache"


def test_watchlist_advanced_metrics_report_insufficient_cache_honestly():
    metrics = compute_watchlist_advanced_metrics(_history(5))

    assert metrics["status"] == "partial"
    assert metrics["return_1w_pct"] is None
    assert metrics["return_1m_pct"] is None
    assert metrics["data_gap"]
    assert metrics["provider_calls"] == 0


def test_progressive_asset_route_precedes_full_fixture_catalog_and_uses_same_origin():
    page = (ROOT / "apps" / "web" / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
    progressive = (
        ROOT / "apps" / "web" / "src" / "components" / "ProgressiveSymbolWorkstation.tsx"
    ).read_text(encoding="utf-8")
    proxy = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "app"
        / "api"
        / "runtime"
        / "[...path]"
        / "route.ts"
    ).read_text(encoding="utf-8")

    assert page.index("if (isAssetRoute)") < page.index("const staticFixtures = await loadAllFixtures()")
    assert 'apiBaseUrl="/api/runtime"' in page
    assert '<Link prefetch={false} key={link.key}' in page
    assert 'data-phase6e-progressive-workstation="true"' in progressive
    assert "/panels/${panel}" in progressive
    assert '"chart-core"' in progressive
    assert "NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL" not in proxy
    assert "GLOBAL_TERMINAL_API_BASE_URL" in proxy
    assert "ALLOWED_RUNTIME_PREFIXES" in proxy


def test_compact_panel_http_etag_and_unknown_symbol_isolation():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from backend.api.app import create_app

    client = TestClient(create_app())
    response = client.get(
        "/api/symbol-workstation/AAPL/panels/chart-core",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
    )
    assert response.status_code == 200
    assert response.headers["etag"]
    assert len(response.content) < 80_000

    conditional = client.get(
        "/api/symbol-workstation/AAPL/panels/chart-core",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
        headers={"If-None-Match": response.headers["etag"]},
    )
    assert conditional.status_code == 304

    unknown = client.get(
        "/api/symbol-workstation/NOTAREAL123/panels/chart-core",
        params={"asset_class": "equity", "runtime_mode": "fixture"},
    )
    assert unknown.status_code == 404
    assert "AAPL" not in unknown.text
    assert "Apple" not in unknown.text


def test_symbol_etag_ignores_only_volatile_clock_fields():
    from backend.api.app import _stable_payload_etag

    first = {
        "generated_at": "2026-07-02T00:00:00+00:00",
        "data": {
            "symbol": "AAPL",
            "last_price": 201.25,
            "market_clock": {"observation_age_seconds": 10.1},
        },
    }
    second = {
        "generated_at": "2026-07-02T00:00:01+00:00",
        "data": {
            "symbol": "AAPL",
            "last_price": 201.25,
            "market_clock": {"observation_age_seconds": 11.1},
        },
    }
    changed = {
        **second,
        "data": {**second["data"], "last_price": 202.0},
    }

    assert _stable_payload_etag(first) == _stable_payload_etag(second)
    assert _stable_payload_etag(first) != _stable_payload_etag(changed)


def test_primary_alpha_vantage_env_name_is_visible_in_provider_and_layer_registry(monkeypatch):
    from lib.layer_registry import build_layer_registry
    from lib.provider_registry import build_provider_registry

    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "masked-test-value")
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)

    layer = next(
        row for row in build_layer_registry()
        if row["layer_id"] == "alpha_vantage_optional"
    )
    provider = next(
        row for row in build_provider_registry()
        if row["provider_id"] == "alpha_vantage"
    )

    assert layer["is_available"] is True
    assert layer["requires_key"] == "ALPHAVANTAGE_API_KEY"
    assert provider["env_var"] == "ALPHAVANTAGE_API_KEY"
    assert provider["free_mode"] is True
