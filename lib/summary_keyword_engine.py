from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable


KEYWORD_CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "risk driver": ("risk", "volatility", "stress", "drawdown", "war", "conflict", "sanction"),
    "asset affected": ("spy", "qqq", "aapl", "btc", "eth", "oil", "gold", "treasury", "equity", "crypto"),
    "region": ("global", "us", "europe", "mena", "asia", "korea", "china", "red sea", "hormuz"),
    "provider issue": ("provider", "key", "probe", "rate", "unavailable", "missing"),
    "data freshness": ("fresh", "aging", "stale", "historical", "proxy", "estimated"),
    "macro regime": ("macro", "rates", "inflation", "growth", "dollar", "yield"),
    "crypto stress": ("funding", "open interest", "liquidation", "stablecoin", "tvl"),
    "energy/geopolitics": ("energy", "oil", "gas", "shipping", "chokepoint", "ais"),
    "watchlist": ("watchlist", "screen", "mover", "leader", "laggard"),
    "strategy research": ("portfolio", "factor", "strategy", "risk contribution", "backtest"),
}

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "into",
    "data",
    "source",
    "market",
    "current",
}


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def classify_keyword_importance(keyword: str, context: Any | None = None) -> dict[str, Any]:
    keyword_text = str(keyword or "").lower()
    context_text = _flatten_text(context).lower()
    matched = []
    for category, patterns in KEYWORD_CATEGORY_PATTERNS.items():
        if any(pattern in keyword_text for pattern in patterns):
            matched.append(category)
    if not matched:
        for category, patterns in KEYWORD_CATEGORY_PATTERNS.items():
            if any(pattern in context_text for pattern in patterns):
                matched.append(category)
    importance = "high" if matched and any(item in matched for item in ["risk driver", "provider issue", "crypto stress", "energy/geopolitics"]) else "medium" if matched else "low"
    return {
        "keyword": str(keyword),
        "category": matched[0] if matched else "watchlist",
        "categories": matched or ["watchlist"],
        "importance": importance,
        "score": 90 if importance == "high" else 65 if importance == "medium" else 40,
    }


def extract_summary_keywords(payload: Any, *, max_keywords: int = 8) -> list[dict[str, Any]]:
    text = _flatten_text(payload).lower()
    phrases = []
    for category, patterns in KEYWORD_CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in text:
                phrases.append(pattern)
    tokens = [
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text)
        if token not in STOPWORDS and not token.isdigit()
    ]
    counts = Counter(phrases + tokens)
    ranked = [item for item, _ in counts.most_common(max_keywords * 2)]
    seen: set[str] = set()
    keywords = []
    for item in ranked:
        clean = item.strip().replace("_", " ")
        if clean in seen:
            continue
        seen.add(clean)
        keywords.append(classify_keyword_importance(clean, payload))
        if len(keywords) >= max_keywords:
            break
    return keywords


def build_keyword_chips(keywords: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    chips = []
    for item in keywords or []:
        payload = item if isinstance(item, dict) else classify_keyword_importance(str(item))
        chips.append(
            {
                "label": str(payload.get("keyword", "")),
                "category": str(payload.get("category", "watchlist")),
                "importance": str(payload.get("importance", "low")),
                "tooltip": f"{payload.get('category', 'watchlist')} | {payload.get('importance', 'low')} importance",
            }
        )
    return chips


def build_actionable_summary_phrases(payload: Any, *, limit: int = 5) -> list[str]:
    keywords = extract_summary_keywords(payload, max_keywords=limit)
    phrases = []
    for keyword in keywords:
        category = keyword["category"]
        label = keyword["keyword"]
        if category == "provider issue":
            phrases.append(f"Verify provider status for {label}.")
        elif category == "data freshness":
            phrases.append(f"Review freshness labels around {label}.")
        elif category in {"risk driver", "energy/geopolitics", "crypto stress"}:
            phrases.append(f"Inspect {label} as a current risk driver.")
        else:
            phrases.append(f"Compare {label} against related panels.")
    return phrases[:limit]
