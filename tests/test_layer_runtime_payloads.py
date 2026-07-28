from __future__ import annotations

import json
from datetime import datetime, timezone

from lib.data_status import ok_result
from lib.layer_registry import RUNTIME_LAYER_FIELDS, build_layer_runtime_payload, get_default_layers


def _row(**overrides):
    base = {
        "title": "M 5.4 test event",
        "provider": "usgs_earthquake",
        "source": "USGS",
        "source_url": "https://earthquake.usgs.gov/event/test",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "freshness": "fresh",
        "source_status": "fresh",
        "lat": 1.0,
        "lon": 2.0,
    }
    base.update(overrides)
    return base


def _layer(payload, layer_id):
    return next(layer for layer in payload["layers"] if layer["layer_id"] == layer_id)


def test_layer_runtime_payload_is_json_safe_and_counts_live_rows():
    now = datetime.now(timezone.utc).isoformat()
    runtime = {
        "news": [_row(title="Red Sea shipping risk", provider="gdelt", domain="shipping", fetched_at=now)],
        "natural": [_row(fetched_at=now)],
        "crypto": [_row(title="BTC public crypto market state", provider="coingecko_public", fetched_at=now)],
    }
    statuses = [
        ok_result([], source="RSS/GDELT", provider="live_feeds", coverage="1/2 feeds available"),
        ok_result([], source="USGS", provider="usgs_earthquake", coverage="1 row"),
        ok_result([], source="CoinGecko", provider="coingecko_public", coverage="1 row"),
    ]

    payload = build_layer_runtime_payload(runtime, statuses)
    json.dumps(payload, default=str)

    assert all(set(RUNTIME_LAYER_FIELDS).issubset(layer) for layer in payload["layers"])
    assert _layer(payload, "earthquakes")["row_count"] == 1
    assert _layer(payload, "earthquakes")["source_status"] == "live/fresh"
    assert _layer(payload, "crypto")["row_count"] == 1
    assert _layer(payload, "chokepoints")["source_status"] == "proxy/static"


def test_layer_runtime_payload_keeps_unavailable_optional_layers_explicit(monkeypatch):
    monkeypatch.delenv("OPENSKY_CLIENT_ID", raising=False)
    monkeypatch.delenv("OPENSKY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OPENSKY_USERNAME", raising=False)
    monkeypatch.delenv("OPENSKY_PASSWORD", raising=False)
    payload = build_layer_runtime_payload({}, [])

    sanctions = _layer(payload, "sanctions")
    ais = _layer(payload, "ais_unavailable")
    flight = _layer(payload, "flight_tracking_unavailable")

    assert "sanctions" not in get_default_layers()
    assert sanctions["availability"] == "unavailable"
    assert sanctions["row_count"] == 0
    assert "no live sanctions rows" in sanctions["caveat"].lower()

    assert ais["source_status"] == "missing-key"
    assert flight["source_status"] == "missing-key"
    assert ais["row_count"] == 0
    assert flight["row_count"] == 0


def test_layer_runtime_payload_marks_partial_news_rate_limit():
    runtime = {"news": [_row(title="GDELT row", provider="gdelt")]}
    status = ok_result(
        [],
        source="RSS/GDELT",
        provider="live_feeds",
        warning="Partial feed errors: GDELT 429 rate limited.",
        coverage="1/2 feeds available",
    )

    payload = build_layer_runtime_payload(runtime, [status])
    conflicts = _layer(payload, "conflicts")

    assert conflicts["row_count"] == 1
    assert conflicts["availability"] == "limited"
    assert conflicts["source_status"] == "rate-limited"
