from __future__ import annotations

from lib.click_path_engine import build_page_next_actions
from lib.top_command_bar import validate_command_bar_action


def test_goal10b_payloads_avoid_trade_directive_language():
    actions = build_page_next_actions("Overview", {"energy": True, "crypto": True})
    text = " ".join(f"{action['label']} {action['description']}".lower() for action in actions)
    for word in ["buy", "sell", "hold", "enter", "exit", "recommended"]:
        assert word not in text
    assert validate_command_bar_action("sell BTC")["blocked"] is True
