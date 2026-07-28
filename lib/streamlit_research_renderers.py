from __future__ import annotations

from html import escape
import re
from typing import Any


def _safe_text(value: Any) -> str:
    return escape(str(value if value is not None else ""))


def sanitize_markdown_text(text: Any) -> str:
    """Preserve Markdown syntax while escaping raw HTML/script brackets."""
    raw = str(text if text is not None else "")
    raw = re.sub(r"&(?!amp;|lt;|gt;|quot;|#\d+;|#x[0-9a-fA-F]+;)", "&amp;", raw)
    return raw.replace("<", "&lt;").replace(">", "&gt;")


def sanitize_html_preview(text: Any) -> str:
    return escape(str(text if text is not None else ""), quote=True)


def render_safe_markdown(text: Any, st: Any | None = None) -> dict[str, Any]:
    safe = sanitize_markdown_text(text)
    result = {"component": "safe_markdown", "markdown": safe, "rendered": False, "safe_by_default": True, "research_only": True}
    if st is not None:
        st.markdown(safe, unsafe_allow_html=False)
        result["rendered"] = True
    return result


def render_chip_strip(chips: list[dict[str, Any]] | dict[str, Any], st: Any | None = None) -> dict[str, Any]:
    rows = chips.get("chips", []) if isinstance(chips, dict) else chips
    payload = {"component": "chip_strip", "chips": rows, "rendered": False, "research_only": True}
    if st is not None:
        st.caption(" · ".join(_safe_text(chip.get("label") or chip.get("status")) for chip in rows))
        payload["rendered"] = True
    return payload


def render_action_cards(cards: list[dict[str, Any]], st: Any | None = None) -> dict[str, Any]:
    payload = {"component": "action_cards", "cards": cards, "rendered": False, "research_only": True}
    if st is not None:
        for card in cards:
            st.markdown(f"**{_safe_text(card.get('title') or card.get('label'))}**", unsafe_allow_html=False)
            if card.get("caveat"):
                st.caption(_safe_text(card.get("caveat")))
        payload["rendered"] = True
    return payload


def render_command_result_cards(cards: list[dict[str, Any]], st: Any | None = None) -> dict[str, Any]:
    return {**render_action_cards(cards, st=st), "component": "command_result_cards"}


def render_report_sidebar(payload: dict[str, Any], st: Any | None = None) -> dict[str, Any]:
    result = {"component": "report_sidebar", "items": payload.get("items", []), "selected_report_id": payload.get("selected_report_id", ""), "rendered": False, "research_only": True}
    if st is not None:
        st.markdown("### Reports")
        for item in result["items"]:
            prefix = "→ " if item.get("selected") else ""
            st.caption(prefix + _safe_text(item.get("title", "Untitled")))
        result["rendered"] = True
    return result


def render_report_reader(payload: dict[str, Any], st: Any | None = None) -> dict[str, Any]:
    markdown = payload.get("markdown_body") or payload.get("safe_preview") or ""
    safe_markdown = sanitize_markdown_text(markdown)
    result = {"component": "report_reader", "payload": {**payload, "safe_markdown": safe_markdown}, "rendered": False, "safe_by_default": True, "research_only": True}
    if st is not None:
        st.markdown(f"### {_safe_text(payload.get('title', 'Report'))}", unsafe_allow_html=False)
        st.markdown(safe_markdown, unsafe_allow_html=False)
        result["rendered"] = True
    return result


def render_strategy_review_queue(payload: list[dict[str, Any]] | dict[str, Any], st: Any | None = None) -> dict[str, Any]:
    rows = payload.get("review_queue", payload.get("items", [])) if isinstance(payload, dict) else payload
    result = {"component": "strategy_review_queue", "items": rows, "rendered": False, "research_only": True}
    if st is not None:
        st.markdown("### Strategy review queue")
        for row in rows:
            st.caption(_safe_text(row.get("strategy_id") or row.get("commit_id")))
        result["rendered"] = True
    return result


def render_intel_feed(payload: dict[str, Any], st: Any | None = None) -> dict[str, Any]:
    rows = payload.get("rows") or payload.get("feed", {}).get("rows", [])
    result = {"component": "intel_feed", "rows": rows, "rendered": False, "research_only": True}
    if st is not None:
        st.markdown("### Intel Feed")
        for row in rows:
            st.caption(f"{_safe_text(row.get('risk_label'))}: {_safe_text(row.get('title'))}")
        result["rendered"] = True
    return result


def render_live_alerts_panel(payload: dict[str, Any], st: Any | None = None) -> dict[str, Any]:
    result = {"component": "live_alerts_panel", "payload": payload, "rendered": False, "research_only": True}
    if st is not None:
        st.markdown("### Live Alerts")
        st.caption(_safe_text(payload.get("empty_message", "Manual alert context panel.")))
        result["rendered"] = True
    return result


def render_tool_cards(payload: dict[str, Any] | list[dict[str, Any]], st: Any | None = None) -> dict[str, Any]:
    tools = payload.get("tools", []) if isinstance(payload, dict) else payload
    if isinstance(payload, dict) and not tools and payload.get("sections"):
        tools = [tool for section in payload["sections"] for tool in section.get("tools", [])]
    result = {"component": "tool_cards", "tools": tools, "rendered": False, "research_only": True}
    if st is not None:
        for tool in tools:
            st.markdown(f"**{_safe_text(tool.get('tool_name'))}**", unsafe_allow_html=False)
            st.caption(_safe_text(tool.get("caveat", "")))
        result["rendered"] = True
    return result


def render_empty_state(message: str = "No supplied context.", st: Any | None = None) -> dict[str, Any]:
    result = {"component": "empty_state", "message": message, "rendered": False, "research_only": True}
    if st is not None:
        st.info(_safe_text(message))
        result["rendered"] = True
    return result


def sanitize_optional_report_html(html_body: Any) -> str:
    from .report_html_templates import sanitize_optional_report_html as _sanitize
    return _sanitize(html_body)

def render_safe_report_export_html(*, title: str = "Research Report", markdown_body: Any = "", html_body_optional: Any = "") -> str:
    from .report_html_templates import render_safe_report_export_html as _render
    return _render(title=title, markdown_body=markdown_body, html_body_optional=html_body_optional)
