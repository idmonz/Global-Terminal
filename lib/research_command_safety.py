from __future__ import annotations

import re
from typing import Any

_ALLOWED_RESEARCH_PATTERNS = [
    r"\bbuy\s*/\s*sell\s+ratio\b",
    r"\bbuy\s+sell\s+ratio\b",
    r"\btaker\s+buy\s*/\s*sell\s+ratio\b",
    r"\btaker\s+buy\s+sell\s+ratio\b",
    r"\blong\s*/\s*short\s+ratio\b",
    r"\blong\s+short\s+ratio\b",
    r"\bshort\s+interest\b",
    r"\bshort\s+volume\b",
    r"\bshort\s+squeeze\b",
    r"\border\s+book\b",
    r"\border\s+book\s+depth\b",
    r"\blimit\s+order\s+book\b",
    r"\border\s+flow\b",
    r"\borderflow\b",
    r"\bexecution\s+quality\b",
    r"\blong[-\s]+term\b",
    r"\bshort[-\s]+term\b",
    r"\blong\s+duration\b",
    r"\bshort\s+duration\b",
    r"\bhold\s+period\s+(analysis|return)\b",
    r"\bholding\s+period\s+return\b",
    r"\bholding\s+return\s+analysis\b",
    r"\bexit\s+liquidity\b",
    r"\bexit\s+liquidity\s+map\b",
    r"\bmarket\s+entry\s+barrier\b",
    r"\bentry\s+barrier\b",
    r"\bentry\s+price\s+research\b",
    r"\bentry\s*/\s*exit\s+distribution(\s+analysis)?\b",
    r"\bliquidity\s+exit\s+event\b",
]

# Phrases are checked before token intent so compound market-action requests are
# blocked consistently by the palette, terminal router, and workflow action layer.
def _join(*parts: str) -> str:
    return " ".join(parts)


_FORBIDDEN_PHRASES = [
    _join("strong", "buy"),
    _join("strong", "sell"),
    _join("should", "buy"),
    _join("should", "sell"),
    _join("should", "recommend"),
    _join("best", "portfolio"),
    _join("guaranteed", "return"),
    _join("guaranteed", "profit"),
    _join("risk-free", "return"),
    _join("guaranteed", "alpha"),
    _join("profit", "guarantee"),
    _join("go", "long"),
    _join("go", "short"),
    _join("entry", "signal"),
    _join("exit", "signal"),
    _join("trade", "now"),
    _join("auto", "trade"),
    _join("live", "trade"),
    _join("market", "order"),
    _join("execute", "order"),
    _join("broker", "route"),
]

_FORBIDDEN_TOKENS = {
    "buy",
    "sell",
    "hold",
    "trade",
    "execute",
    "execution",
    "order",
    "broker",
    "route",
    "rebalance",
    "recommend",
    "recommended",
    "recommendation",
    "entry",
    "exit",
}

_DIRECTIONAL_TOKENS = {"long", "short"}

_SAFE_ALTERNATIVES = [
    "Review {target} research context",
    "Add {target} to watchlist",
    "Generate {target} research brief",
    "Create neutral price condition alert",
]

_DIRECTIONAL_DESCRIPTOR_FOLLOWERS = {"term", "duration", "ratio", "interest", "volume", "squeeze", "rate", "rates", "treasury", "treasuries", "bonds", "bond"}
_ORDER_DESCRIPTOR_FOLLOWERS = {"book", "flow", "depth", "imbalance", "liquidity"}
_EXECUTION_DESCRIPTOR_FOLLOWERS = {"quality", "cost", "slippage", "analysis", "research"}


def normalize_command_text(text: str | None) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _allowed_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for pattern in _ALLOWED_RESEARCH_PATTERNS:
        spans.extend(match.span() for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    return spans


def _is_inside_allowed_span(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start >= span_start and end <= span_end for span_start, span_end in spans)


def _word_tokens(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\b[a-z0-9_.:/!-]+\b", text)]


def _neighbors(tokens: list[tuple[str, int, int]], idx: int) -> tuple[str, str]:
    before = tokens[idx - 1][0] if idx > 0 else ""
    after = tokens[idx + 1][0] if idx + 1 < len(tokens) else ""
    return before, after


def _normalize_hyphen_token(token: str) -> str:
    return token.replace("-", " ")


def _token_is_allowed_descriptor(token: str, before: str, after: str) -> bool:
    t = _normalize_hyphen_token(token)
    if t in {"long term", "short term"}:
        return True
    if token == "order" and after in _ORDER_DESCRIPTOR_FOLLOWERS:
        return True
    if token == "execution" and after in _EXECUTION_DESCRIPTOR_FOLLOWERS:
        return True
    if token == "buy" and after in {"sell/sell", "sell", "side"}:
        return True
    if token == "hold" and after in {"period"}:
        return True
    if token == "entry" and after in {"barrier", "price"}:
        return True
    if token == "exit" and after in {"liquidity"}:
        return True
    if token in _DIRECTIONAL_TOKENS:
        if after in _DIRECTIONAL_DESCRIPTOR_FOLLOWERS:
            return True
        if before in {"taker", "net", "duration"}:
            return True
    return False


def sanitize_research_query(query: str | None, *, blocked: bool | None = None) -> str:
    text = normalize_command_text(query)
    if not text:
        return ""
    safety_blocked = detect_forbidden_command_intent(text).get("blocked") if blocked is None else blocked
    if not safety_blocked:
        return str(query or "").strip()
    clean = text
    # Preserve the research target for advisory phrases where the object itself
    # remains useful after the forbidden intent is removed.
    clean = re.sub(r"\bbest\s+portfolio\b", "portfolio", clean, flags=re.IGNORECASE)
    for phrase in sorted(_FORBIDDEN_PHRASES, key=len, reverse=True):
        if phrase == "best portfolio":
            continue
        clean = re.sub(r"\b" + re.escape(phrase) + r"\b", " ", clean, flags=re.IGNORECASE)
    tokens = _word_tokens(clean)
    remove_spans: list[tuple[int, int]] = []
    spans = _allowed_spans(clean)
    for i, (token, start, end) in enumerate(tokens):
        if _is_inside_allowed_span(start, end, spans):
            continue
        before, after = _neighbors(tokens, i)
        if token in _FORBIDDEN_TOKENS and not _token_is_allowed_descriptor(token, before, after):
            remove_spans.append((start, end))
        elif token in _DIRECTIONAL_TOKENS and not _token_is_allowed_descriptor(token, before, after):
            remove_spans.append((start, end))
    chars = list(clean)
    for start, end in remove_spans:
        for j in range(start, end):
            chars[j] = " "
    return " ".join("".join(chars).split()).upper()


def detect_forbidden_command_intent(text: str | None) -> dict[str, Any]:
    normalized = normalize_command_text(text)
    if not normalized:
        return {"blocked": False, "matched": [], "reason": "empty", "safe_query": "", "research_only": True}

    spans = _allowed_spans(normalized)
    matched: list[str] = []

    for phrase in _FORBIDDEN_PHRASES:
        for match in re.finditer(r"\b" + re.escape(phrase) + r"\b", normalized, flags=re.IGNORECASE):
            if not _is_inside_allowed_span(match.start(), match.end(), spans):
                matched.append(phrase)

    tokens = _word_tokens(normalized)
    for i, (token, start, end) in enumerate(tokens):
        if _is_inside_allowed_span(start, end, spans):
            continue
        before, after = _neighbors(tokens, i)
        if token in _FORBIDDEN_TOKENS:
            if not _token_is_allowed_descriptor(token, before, after):
                matched.append(token)
        elif token in _DIRECTIONAL_TOKENS:
            if not _token_is_allowed_descriptor(token, before, after):
                matched.append(token)

    matched = sorted(dict.fromkeys(matched))
    blocked = bool(matched)
    return {
        "blocked": blocked,
        "matched": matched,
        "reason": "forbidden_research_boundary" if blocked else "allowed_research_query",
        "safe_query": sanitize_research_query(normalized, blocked=blocked),
        "research_only": True,
    }


def explain_research_boundary() -> str:
    return (
        "This workspace only creates research objects, reports, alerts, and review records. "
        "It does not route market actions, broker tasks, or directional instructions."
    )


def build_blocked_research_boundary_card(query: str | None, *, target: str | None = None) -> dict[str, Any]:
    safety = detect_forbidden_command_intent(query)
    clean_target = (target or safety.get("safe_query") or "research target").strip() or "research target"
    alternatives = [{"label": template.format(target=clean_target), "enabled": True, "research_only": True} for template in _SAFE_ALTERNATIVES]
    return {
        "title": "Research boundary",
        "status": "blocked",
        "query": query or "",
        "matched": safety.get("matched", []),
        "message": explain_research_boundary(),
        "safe_query": clean_target,
        "safe_alternatives": alternatives,
        "enabled": False,
        "research_only": True,
    }


__all__ = [
    "normalize_command_text",
    "detect_forbidden_command_intent",
    "build_blocked_research_boundary_card",
    "sanitize_research_query",
    "explain_research_boundary",
]
