from __future__ import annotations

from lib.market_briefing_cards import provider_health_card
from lib.terminal_ui import status_badge


def test_terminal_visual_density_badges_and_cards():
    assert "terminal-badge" in status_badge("Proxy", tone="estimated")
    card = provider_health_card({"ready_count": 2, "gap_count": 1})
    assert card["tags"] == ["provider health"]
