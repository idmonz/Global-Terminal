from __future__ import annotations

from lib.energy_market_impact import build_energy_market_impact_cards, compute_chokepoint_oil_impact


def test_energy_market_impact_uses_proxy_language():
    cards = build_energy_market_impact_cards()
    choke = compute_chokepoint_oil_impact()

    assert cards
    assert choke["is_proxy"] is True
    assert "causality" in choke["caveat"].lower()
