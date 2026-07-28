from __future__ import annotations

from lib.visual_tokens import CARD_RADIUS, build_token_css, get_visual_tokens, status_badge_tokens


def test_visual_tokens_are_modern_dark_friendly():
    tokens = get_visual_tokens()
    assert tokens["card_radius"] == CARD_RADIUS
    assert tokens["neutral"]["bg"].startswith("#")
    assert status_badge_tokens("historical-only")["label"] == "Historical Only"
    assert "orange" not in build_token_css().lower()
