from __future__ import annotations

from typing import Any

from .executive_summary_engine import build_global_executive_summary, build_workspace_executive_summary
from .market_briefing_cards import (
    affected_assets_card,
    data_confidence_card,
    provider_health_card,
    proxy_warning_card,
    risk_state_card,
    what_changed_card,
)


def build_terminal_briefing_payload(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = build_global_executive_summary(payload)
    cards = [
        risk_state_card(summary["global_risk_state"]),
        what_changed_card(summary["key_changes"]),
        affected_assets_card(summary["affected_assets"]),
        data_confidence_card(summary["data_confidence"]["score"], summary["missing_data"]),
        proxy_warning_card(summary["proxy_outputs"]),
        provider_health_card(summary["provider_health"]),
    ]
    return {"summary": summary, "cards": cards, "next_drilldowns": summary["next_drilldowns"]}


def build_workspace_briefing_payload(workspace: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = build_workspace_executive_summary(workspace, payload)
    brief = build_terminal_briefing_payload(payload)
    brief["summary"] = summary
    return brief
