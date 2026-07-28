from __future__ import annotations

import re
from typing import Iterable


DISCLOSURE = (
    "This dashboard is for educational and informational purposes only. "
    "It is not financial advice, not a recommendation to buy or sell any security, "
    "and is not personalized to your situation. Consult a licensed advisor before making investment decisions."
)

AI_DISCLOSURE = "AI summary; verify with primary data. Not financial advice."

FORBIDDEN_PATTERNS = {
    r"\bstrong\s+buy\b": "constructive technical backdrop",
    r"\bstrong\s+sell\b": "elevated downside risk watch-point",
    r"\bshould\s+buy\b": "may show constructive evidence",
    r"\bshould\s+sell\b": "may show downside risk evidence",
    r"\btarget\s+price\s+recommendation\b": "technical level context",
    r"\btime\s+to\s+enter\b": "monitoring watch-point",
    r"\btime\s+to\s+exit\b": "risk boundary",
    r"\bgo\s+long\b": "upside exposure context",
    r"\bgo\s+short\b": "downside exposure context",
    r"\blong\s+this\b": "upside exposure context",
    r"\bshort\s+this\b": "downside exposure context",
    r"\blonging\b": "upside exposure context",
    r"\bshorting\b": "downside exposure context",
    r"\bbuy\b": "constructive watch-point",
    r"\bsell\b": "elevated downside risk watch-point",
    r"\bhold\b": "neutral / mixed evidence",
    r"\brecommendation\b": "neutral research note",
    r"\brecommend\b": "frame as a watch-point",
    r"\benter(?:ing)?\b": "monitoring",
    r"\bexit(?:ing)?\b": "risk boundary",
    r"\ballocat(?:e|ion|ing)\b": "exposure context",
}

ALLOWED_MARKET_STRUCTURE_PATTERNS = [
    r"\blong/short\s+(?:ratio|bias|account|position|exposure)\b",
    r"\blong\s+(?:account|liquidation|exposure|pressure|side)\b",
    r"\bshort\s+(?:account|liquidation|exposure|pressure|side)\b",
    r"\btop\s+trader\s+long/short\b",
    r"\bglobal\s+long/short\b",
    r"\btaker\s+buy/sell\b",
    r"\bbuy/sell\s+ratio\b",
    r"\bbuy\s+volume\b",
    r"\bsell\s+volume\b",
]


def _mask_allowed_market_structure(text: str) -> tuple[str, dict[str, str]]:
    masked = text or ""
    replacements: dict[str, str] = {}
    for pattern in ALLOWED_MARKET_STRUCTURE_PATTERNS:
        def replace(match: re.Match) -> str:
            token = f"__MARKET_STRUCTURE_TERM_{len(replacements)}__"
            replacements[token] = match.group(0)
            return token

        masked = re.sub(pattern, replace, masked, flags=re.IGNORECASE)
    return masked, replacements


def sanitize_financial_language(text: str) -> str:
    cleaned, replacements = _mask_allowed_market_structure(text or "")
    for pattern, replacement in FORBIDDEN_PATTERNS.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    for token, original in replacements.items():
        cleaned = cleaned.replace(token, original)
    return cleaned


def sanitize_text(text: str) -> str:
    return sanitize_financial_language(text)


def contains_forbidden_language(text: str, *, allow_disclosure: bool = True) -> bool:
    candidate = text or ""
    if allow_disclosure:
        candidate = candidate.replace(DISCLOSURE, "")
        candidate = candidate.replace(AI_DISCLOSURE, "")
    candidate, _ = _mask_allowed_market_structure(candidate)
    return any(re.search(pattern, candidate, flags=re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS)


def find_forbidden_terms(text: str, *, allow_disclosure: bool = True) -> list[str]:
    candidate = text or ""
    if allow_disclosure:
        candidate = candidate.replace(DISCLOSURE, "")
        candidate = candidate.replace(AI_DISCLOSURE, "")
    candidate, _ = _mask_allowed_market_structure(candidate)
    return [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, candidate, flags=re.IGNORECASE)]


def assert_clean_texts(texts: Iterable[str]) -> None:
    violations = [text for text in texts if contains_forbidden_language(text)]
    if violations:
        raise ValueError(f"Forbidden language detected in {len(violations)} text fragment(s).")


def neutral_scenario_label(score: float | int | None) -> str:
    if score is None:
        return "Neutral / mixed evidence"
    if score >= 0.65:
        return "Constructive technical backdrop"
    if score <= 0.35:
        return "Elevated downside risk"
    return "Neutral / mixed evidence"


def render_disclosure(st_module) -> None:
    st_module.caption(DISCLOSURE)
