from pathlib import Path


def test_goal11_has_no_broker_execution_functions():
    text = "\n".join(
        p.read_text(encoding="utf-8").lower()
        for p in Path("lib").glob("*.py")
        if any(k in p.name for k in ["research", "workspace", "watchlist", "alert", "report", "strategy"])
    )
    for token in ["place_order", "order_routing", "broker_execute", "trade_approval"]:
        assert token not in text
