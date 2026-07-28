from __future__ import annotations

import re
from typing import Iterable

from .config import AI_DISCLOSURE


FORBIDDEN_RECOMMENDATION_TERMS = [
    "Strong Buy",
    "Strong Sell",
    "Should buy",
    "Should sell",
    "Time to enter",
    "Time to exit",
    "Go long",
    "Go short",
    "Long this",
    "Short this",
    "Entry signal",
    "Exit signal",
    "Trade now",
    "Recommendation",
    "Recommended",
    "Buy",
    "Sell",
    "Hold",
]

ALLOWED_MARKET_CONTEXT_TERMS = [
    "long/short ratio",
    "short interest",
    "long liquidation",
    "short liquidation",
    "downside scenario",
    "upside scenario",
    "short-term",
    "long-term",
    "long-duration bonds",
    "short-duration bonds",
    "gamma exposure",
    "options open interest",
    "taker buy/sell",
    "buy/sell ratio",
    "buy volume",
    "sell volume",
]

SECRET_PATTERNS = [
    r"sk-ant-[A-Za-z0-9_\-]+",
    r"AIza[0-9A-Za-z_\-]+",
    r"gsk_[A-Za-z0-9_\-]+",
    r"sk-or-v1-[A-Za-z0-9_\-]+",
    r"(?i)(ANTHROPIC_API_KEY|GEMINI_API_KEY|GOOGLE_API_KEY|GROQ_API_KEY|OPENROUTER_API_KEY)\s*=\s*[^\s,;]+",
]

REPLACEMENTS = {
    "strong buy": "constructive evidence cluster",
    "strong sell": "elevated downside risk cluster",
    "should buy": "may show constructive evidence",
    "should sell": "may show downside risk evidence",
    "time to enter": "timing-sensitive watch-point",
    "time to exit": "risk boundary watch-point",
    "go long": "upside exposure context",
    "go short": "downside exposure context",
    "long this": "upside exposure context",
    "short this": "downside exposure context",
    "entry signal": "trigger watch-point",
    "exit signal": "risk boundary watch-point",
    "trade now": "monitor current conditions",
    "recommendation": "neutral research note",
    "recommended": "noted",
    "buy": "constructive watch-point",
    "sell": "downside risk watch-point",
    "hold": "mixed evidence",
}


def forbidden_recommendation_terms() -> list[str]:
    return list(FORBIDDEN_RECOMMENDATION_TERMS)


def allowed_market_context_terms() -> list[str]:
    return list(ALLOWED_MARKET_CONTEXT_TERMS)


def _mask_allowed_terms(text: str) -> tuple[str, dict[str, str]]:
    masked = text or ""
    replacements: dict[str, str] = {}
    for term in ALLOWED_MARKET_CONTEXT_TERMS:
        pattern = re.escape(term).replace(r"\ ", r"\s+")

        def replace(match: re.Match) -> str:
            token = f"__AI_ALLOWED_TERM_{len(replacements)}__"
            replacements[token] = match.group(0)
            return token

        masked = re.sub(pattern, replace, masked, flags=re.IGNORECASE)
    return masked, replacements


def _unmask_terms(text: str, replacements: dict[str, str]) -> str:
    restored = text
    for token, original in replacements.items():
        restored = restored.replace(token, original)
    return restored


def redact_secrets(text: str | None) -> str:
    redacted = text or ""
    for pattern in SECRET_PATTERNS:
        redacted = re.sub(pattern, "[REDACTED_SECRET]", redacted)
    return redacted


def clean_ai_output(text: str | None) -> str:
    cleaned, allowed = _mask_allowed_terms(redact_secrets(text))
    for term in sorted(REPLACEMENTS, key=len, reverse=True):
        replacement = REPLACEMENTS[term]
        cleaned = re.sub(rf"\b{re.escape(term)}\b", replacement, cleaned, flags=re.IGNORECASE)
    return _unmask_terms(cleaned, allowed).strip()


def validate_ai_output(text: str | None) -> tuple[bool, list[str]]:
    candidate, _ = _mask_allowed_terms(redact_secrets(text))
    violations: list[str] = []
    for term in FORBIDDEN_RECOMMENDATION_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", candidate, flags=re.IGNORECASE):
            violations.append(term)
    return not violations, violations


def append_ai_disclosure(text: str | None) -> str:
    body = (text or "").strip()
    if AI_DISCLOSURE.lower() in body.lower():
        return body
    return f"{body}\n\n_{AI_DISCLOSURE}_" if body else f"_{AI_DISCLOSURE}_"


def ai_output_to_safe_markdown(text: str | None) -> str:
    return append_ai_disclosure(clean_ai_output(text))


def assert_safe_outputs(texts: Iterable[str]) -> None:
    violations = []
    for text in texts:
        ok, terms = validate_ai_output(text)
        if not ok:
            violations.extend(terms)
    if violations:
        raise ValueError(f"Forbidden AI language detected: {sorted(set(violations))}")
