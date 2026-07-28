from __future__ import annotations

from lib.shipping_chokepoint_engine import build_chokepoint_risk_cards, compute_shipping_disruption_proxy


def test_chokepoint_engine_returns_proxy_scores():
    cards = build_chokepoint_risk_cards()
    proxy = compute_shipping_disruption_proxy()

    assert cards[0]["is_proxy"] is True
    assert 0 <= proxy["shipping_disruption_proxy"] <= 100
