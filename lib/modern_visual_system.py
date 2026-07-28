from __future__ import annotations

from typing import Any, Iterable

from .click_path_engine import build_click_path_cards
from .summary_keyword_engine import build_keyword_chips, extract_summary_keywords
from .ui_action_cards import build_action_card_deck
from .visual_tokens import build_token_css, data_quality_tone, get_visual_tokens, risk_tone


def build_data_confidence_badge(confidence: float | int | str | None, status: str = "estimated") -> dict[str, Any]:
    tone = data_quality_tone(status)
    return {"label": "Data Confidence", "value": "N/A" if confidence is None else confidence, "status": tone["status"], "color": tone["color"]}


def build_source_freshness_badge(status: str | None, source: str | None = None) -> dict[str, Any]:
    tone = data_quality_tone(status)
    return {"label": source or "Source", "value": tone["label"], "status": tone["status"], "color": tone["color"]}


def build_modern_card(
    title: str,
    summary: str,
    *,
    severity: str = "watch",
    source: str = "terminal",
    freshness: str = "estimated",
    confidence: float | int | str | None = None,
    click_action: dict[str, Any] | None = None,
    tags: Iterable[str] | None = None,
) -> dict[str, Any]:
    risk = risk_tone(severity)
    return {
        "title": title,
        "summary": summary,
        "severity": risk["severity"],
        "risk_color": risk["color"],
        "source": source,
        "freshness": build_source_freshness_badge(freshness, source),
        "confidence": build_data_confidence_badge(confidence, freshness),
        "click_action": click_action,
        "tags": list(tags or []),
    }


def build_metric_card(label: str, value: Any, *, delta: Any = None, status: str = "estimated", source: str = "terminal", tooltip: str | None = None) -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "delta": delta,
        "status": status,
        "source": source,
        "tooltip": tooltip or f"{label} from {source}; status {status}.",
        "freshness": build_source_freshness_badge(status, source),
    }


def build_summary_panel(
    title: str,
    bullets: Iterable[str] | None = None,
    *,
    keywords: Iterable[Any] | None = None,
    actions: Iterable[dict[str, Any]] | None = None,
    confidence: float | int | str | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "bullets": list(bullets or []),
        "keywords": build_keyword_chips(keywords),
        "actions": build_action_card_deck(actions),
        "confidence": build_data_confidence_badge(confidence, "estimated"),
    }


def build_modern_page_header(
    title: str,
    subtitle: str = "",
    *,
    keywords: Iterable[Any] | None = None,
    freshness: str = "unknown",
    confidence: float | int | str | None = None,
    actions: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "subtitle": subtitle,
        "keywords": build_keyword_chips(keywords),
        "freshness": build_source_freshness_badge(freshness),
        "confidence": build_data_confidence_badge(confidence, freshness),
        "actions": build_action_card_deck(actions),
    }


def build_visual_system_payload(page_title: str, summary: Any, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    keywords = extract_summary_keywords({"summary": summary, **context})
    actions = build_click_path_cards(page_title, {"summary": summary, **context})
    return {
        "tokens": get_visual_tokens(),
        "css": build_token_css(),
        "header": build_modern_page_header(page_title, str(summary), keywords=keywords, freshness=str(context.get("freshness", "estimated")), confidence=context.get("confidence")),
        "summary": build_summary_panel(page_title, [str(summary)], keywords=keywords, actions=actions, confidence=context.get("confidence")),
        "click_paths": actions,
    }
