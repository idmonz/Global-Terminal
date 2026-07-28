from __future__ import annotations

import re


BLOCKED_TERMS = [
    "buy",
    "sell",
    "hold",
    "strong buy",
    "strong sell",
    "go long",
    "go short",
    "entry signal",
    "exit signal",
    "trade now",
    "best portfolio",
    "guaranteed return",
]


def contains_blocked_signal_language(text: str) -> bool:
    lower = str(text or "").lower()
    return any(re.search(rf"\b{re.escape(term)}\b", lower) for term in BLOCKED_TERMS)


def neutralize_signal_language(text: str) -> str:
    replacements = {
        "bullish": "constructive",
        "bearish": "deteriorating",
        "buy": "inspect",
        "sell": "review",
        "hold": "monitor",
        "go long": "research constructive exposure",
        "go short": "research downside exposure",
        "entry signal": "research trigger",
        "exit signal": "risk trigger",
        "best portfolio": "highest-ranked research bundle",
    }
    output = str(text or "")
    for source, target in replacements.items():
        output = re.sub(rf"\b{re.escape(source)}\b", target, output, flags=re.IGNORECASE)
    return output


def assert_research_only_text(text: str) -> bool:
    return not contains_blocked_signal_language(neutralize_signal_language(text))
