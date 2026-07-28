from __future__ import annotations

from typing import Any


def explain_drilldown_reason(candidate: dict[str, Any]) -> str:
    reason = candidate.get("reason") or "Inspect source-labeled evidence in the linked workspace."
    return str(reason)


def build_drilldown_candidates(context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    gaps = list(context.get("data_gaps", []))
    risk_state = str(context.get("risk_state", context.get("global_risk_state", "watch"))).lower()
    candidates = [
        {"label": "Open War Room - Chokepoint layer", "command": "GLOBAL WAR", "page": "pages/14_War_Room.py", "priority": 70 if risk_state in {"elevated", "stressed", "critical"} else 45, "reason": "Event and chokepoint layers can explain cross-asset stress channels."},
        {"label": "Open Portfolio Quant Lab - Factor coverage", "command": "SPY PORT", "page": "pages/16_Portfolio_Quant_Lab.py", "priority": 62, "reason": "Portfolio factor coverage shows which exposures rely on proxy data."},
        {"label": "Open Financial Terminal - Revenue / margin details", "command": "AAPL FA", "page": "pages/15_Financial_Terminal.py", "priority": 54, "reason": "Financial statements help inspect security-level fundamentals."},
        {"label": "Open Provider Center - Missing API keys", "command": "DATA PROBE", "page": "pages/17_Data_Provider_Center.py", "priority": 80 if gaps else 44, "reason": "Provider diagnostics identify missing keys, stale feeds, and source limitations."},
        {"label": "Open Crypto Intelligence - Funding/OI stress", "command": "BTC CRYPTO", "page": "pages/8_Crypto_Intelligence.py", "priority": 58, "reason": "Crypto derivatives panels show funding, open interest, and proxy stress labels."},
    ]
    return candidates


def rank_drilldown_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((dict(item) for item in candidates), key=lambda item: item.get("priority", 0), reverse=True)


def build_drilldown_cards(context: dict[str, Any] | None = None, limit: int = 4) -> list[dict[str, Any]]:
    cards = []
    for item in rank_drilldown_candidates(build_drilldown_candidates(context))[:limit]:
        cards.append(
            {
                "title": item["label"],
                "summary": explain_drilldown_reason(item),
                "severity": "watch" if item.get("priority", 0) < 70 else "medium",
                "tags": [item["command"], "drill down"],
                "command": item["command"],
                "page": item["page"],
                "freshness": "estimated",
            }
        )
    return cards
