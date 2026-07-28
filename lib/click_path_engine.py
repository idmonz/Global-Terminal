from __future__ import annotations

from typing import Any

from .ui_action_cards import build_action_card, build_page_action_rail


def build_contextual_drilldowns(item: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    item = item or {}
    context = context or {}
    symbol = str(item.get("symbol") or item.get("ticker") or context.get("symbol") or "").upper()
    region = str(item.get("region") or item.get("country") or context.get("region") or "")
    provider = str(item.get("provider") or item.get("source") or "")
    actions = []
    if symbol:
        actions.append(build_action_card(f"Open {symbol}", "Inspect asset detail, source status, and related panels.", command=f"{symbol} FA", page="pages/15_Financial_Terminal.py"))
    if region:
        actions.append(build_action_card(f"Open {region} layer", "Review regional events, confidence, and affected assets.", command=f"WAR ROOM {region}", page="pages/14_War_Room.py"))
    if provider:
        actions.append(build_action_card(f"Verify {provider}", "Check probe state, freshness, and missing-key guidance.", command="DATA PROBE", page="pages/17_Data_Provider_Center.py"))
    return actions


def build_page_next_actions(page: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return build_page_action_rail(page, context)


def build_click_path_cards(page: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    cards = [
        build_action_card("What this page says", str(context.get("summary") or "A summary-first view of current market and intelligence evidence."), status="context"),
        build_action_card("What changed", str(context.get("what_changed") or "Review the latest deltas, event clusters, and provider status."), status="context"),
        build_action_card("Inspect next", "Use the cards below to drill into the most relevant workspace.", status="available"),
    ]
    if page in {"app.py", "pages/14_War_Room.py", "pages/9_Energy_Geopolitics.py", "pages/16_Portfolio_Quant_Lab.py", "pages/17_Data_Provider_Center.py"}:
        cards.append(build_action_card("Open Research Workspace", "Review watchlist, alert, report, and strategy records.", command="WORKSPACE", page="pages/19_Research_Workspace.py"))
        cards.append(build_action_card("Open Watchlist & Alerts", "Inspect enriched watchlist context and manual alert state.", command="WATCHLIST", page="pages/20_Watchlist_Alerts.py"))
        cards.append(build_action_card("Open Report Inbox", "Review generated research briefs and provider caveats.", command="REPORTS", page="pages/21_Report_Inbox.py"))
        cards.append(build_action_card("Open Strategy Decision Log", "Review strategy research commits and guard results.", command="STRATEGY LOG", page="pages/22_Strategy_Decision_Log.py"))
    cards.extend(build_page_next_actions(page, context))
    return cards


def build_user_click_map(page: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    cards = build_click_path_cards(page, context)
    return {
        "page": page,
        "cards": cards,
        "clickable_count": sum(1 for card in cards if card.get("clickable")),
        "commands": [card["command"] for card in cards if card.get("command")],
        "pages": [card["page"] for card in cards if card.get("page")],
    }
