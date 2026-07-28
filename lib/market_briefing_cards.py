from __future__ import annotations

from typing import Any

from .click_path_engine import build_page_next_actions
from .summary_keyword_engine import extract_summary_keywords


def _card(title: str, summary: str, *, severity: str = "watch", tags: list[str] | None = None, freshness: str = "estimated") -> dict[str, Any]:
    return {"title": title, "summary": summary, "severity": severity, "tags": tags or [], "freshness": freshness}


def risk_state_card(state: str, score: float | int | None = None) -> dict[str, Any]:
    return _card("Risk State", f"Current risk state is {state}. Score: {score if score is not None else 'N/A'}.", severity="medium" if str(state).lower() in {"elevated", "stressed"} else "watch", tags=["risk state"])


def what_changed_card(changes: list[str] | None = None) -> dict[str, Any]:
    text = "; ".join(changes or ["No major changes detected in the supplied payload."])
    return _card("What Changed", text, tags=["change log"])


def affected_assets_card(assets: list[str] | None = None) -> dict[str, Any]:
    return _card("Affected Assets", ", ".join(assets or ["No asset list supplied."]), tags=["assets"])


def data_confidence_card(confidence: float | int | None = None, gaps: list[str] | None = None) -> dict[str, Any]:
    summary = f"Source confidence: {confidence if confidence is not None else 'N/A'}. Data gaps: {len(gaps or [])}."
    return _card("Data Confidence", summary, severity="watch" if gaps else "low", tags=["source confidence", "data quality"])


def proxy_warning_card(proxies: list[str] | None = None) -> dict[str, Any]:
    return _card("Proxy / Estimate Labels", "; ".join(proxies or ["No proxy outputs were supplied."]), severity="medium" if proxies else "low", tags=["proxy", "estimated"])


def next_drilldown_card(label: str, reason: str, command: str | None = None) -> dict[str, Any]:
    return _card(label, reason, tags=[tag for tag in [command, "drill down"] if tag])


def source_freshness_card(status: str, source: str | None = None) -> dict[str, Any]:
    return _card("Source Freshness", f"{source or 'Source'} freshness is {status}.", severity="medium" if status in {"stale", "missing"} else "low", tags=["freshness"], freshness=status)


def regime_card(regime: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(regime, dict):
        summary = f"{regime.get('state', 'mixed')} | score {regime.get('score', 'N/A')}"
        tags = [str(item) for item in regime.get("drivers", [])[:3]]
    else:
        summary, tags = str(regime), ["regime"]
    return _card("Regime", summary, tags=tags)


def watchpoint_card(point: str, severity: str = "watch") -> dict[str, Any]:
    return _card("Watchpoint", point, severity=severity, tags=["watchpoint"])


def provider_health_card(summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or {}
    text = f"Ready: {summary.get('ready_count', summary.get('available', 0))}; gaps: {summary.get('gap_count', summary.get('optional_missing', 0))}."
    return _card("Provider Health", text, severity="medium" if summary.get("gap_count") or summary.get("optional_missing") else "low", tags=["provider health"])


def missing_key_card(env_var: str, provider: str | None = None) -> dict[str, Any]:
    return _card("Missing Key", f"{provider or 'Provider'} is missing {env_var}; base launch remains available.", severity="watch", tags=["missing key", env_var])


def modern_market_briefing_deck(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    state = payload.get("risk_state") or payload.get("state") or "watch"
    gaps = list(payload.get("data_gaps") or [])
    cards = [
        risk_state_card(str(state), payload.get("risk_score")),
        what_changed_card(payload.get("key_changes")),
        data_confidence_card(payload.get("data_confidence"), gaps),
        provider_health_card(payload.get("provider_health")),
    ]
    return {
        "cards": cards,
        "keywords": extract_summary_keywords(payload),
        "next_actions": build_page_next_actions("Overview", payload),
        "caveat": "Briefing cards are research context and avoid trade execution language.",
    }
