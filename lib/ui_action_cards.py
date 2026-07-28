from __future__ import annotations

from typing import Any, Iterable


BLOCKED_WORDS = {"buy", "sell", "hold", "trade", "enter", "exit", "recommended"}


def _neutralize(text: str) -> str:
    clean = str(text or "")
    for word in BLOCKED_WORDS:
        clean = clean.replace(word, "review").replace(word.title(), "Review").replace(word.upper(), "REVIEW")
    return clean


def build_action_card(
    label: str,
    description: str,
    *,
    command: str | None = None,
    page: str | None = None,
    status: str = "available",
    source: str = "terminal",
    tooltip: str | None = None,
) -> dict[str, Any]:
    return {
        "label": _neutralize(label),
        "description": _neutralize(description),
        "command": command,
        "page": page,
        "status": status,
        "source": source,
        "tooltip": tooltip or _neutralize(description),
        "clickable": bool(command or page),
    }


def build_action_card_deck(actions: Iterable[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [
        build_action_card(
            str(item.get("label", "Open panel")),
            str(item.get("description", "Inspect the related panel.")),
            command=item.get("command"),
            page=item.get("page"),
            status=str(item.get("status", "available")),
            source=str(item.get("source", "terminal")),
            tooltip=item.get("tooltip"),
        )
        for item in actions or []
    ]


def build_page_action_rail(page: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    page_key = str(page or "overview").lower()
    actions = [
        {"label": "Open War Room", "description": "Inspect map-first event layers and source gaps.", "command": "WR", "page": "pages/14_War_Room.py"},
        {"label": "Open Provider Center", "description": "Verify provider health, keys, probes, and freshness.", "command": "DATA PROBE", "page": "pages/17_Data_Provider_Center.py"},
    ]
    if "crypto" in page_key or context.get("crypto"):
        actions.insert(0, {"label": "Review Crypto Stress", "description": "Compare price, funding, OI, and liquidation pressure proxies.", "command": "BTC CRYPTO", "page": "pages/8_Crypto_Intelligence.py"})
    if "energy" in page_key or context.get("energy"):
        actions.insert(0, {"label": "Review Energy Map", "description": "Inspect chokepoints, weather, news, and shipping caveats.", "command": "CL ENERGY", "page": "pages/9_Energy_Geopolitics.py"})
    if "portfolio" in page_key or context.get("portfolio"):
        actions.insert(0, {"label": "Review Portfolio Lab", "description": "Compare exposures, risk contribution, and data quality.", "command": "SPY PORT", "page": "pages/16_Portfolio_Quant_Lab.py"})
    return build_action_card_deck(actions[:6])
