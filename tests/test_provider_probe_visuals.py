from __future__ import annotations

from lib.provider_probe_visuals import build_provider_probe_metric_cards, build_provider_probe_table


def test_provider_probe_visual_payloads():
    results = [{"provider_id": "sec_edgar", "provider": "SEC", "ok": False, "status": "missing_key"}]
    assert build_provider_probe_metric_cards(results)[2]["value"] == 1
    assert len(build_provider_probe_table(results)) == 1
