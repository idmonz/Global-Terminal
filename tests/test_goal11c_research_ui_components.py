from lib.research_ui_components import (
    build_compact_metric_row,
    build_empty_state_panel,
    build_event_severity_badge,
    build_methodology_tooltip_payload,
    build_next_action_buttons,
    build_provider_caveat_chips,
    build_research_card_deck,
    build_source_freshness_strip,
    build_status_chip_row,
)


def test_goal11c_research_ui_component_payloads():
    strip = build_source_freshness_strip([{"source": "demo", "freshness": "missing-key", "confidence": "low"}])
    assert strip["chips"][0]["status"] == "missing-key"
    assert build_provider_caveat_chips([{"provider_id": "fred", "requires_key": True, "is_configured": False}])[0]["status"] == "missing-key"
    assert build_event_severity_badge("critical")["label"] == "CRITICAL"
    assert build_methodology_tooltip_payload("panel")["research_only"] is True
    assert build_research_card_deck([{"title": "A"}])["cards"][0]["next_action"] == "review"
    assert build_empty_state_panel("Empty")["state"] == "empty"
    assert build_next_action_buttons([{"label": "Review", "command": "REVIEW"}])[0]["research_only"] is True
    assert build_status_chip_row([{"label": "fresh"}])[0]["label"] == "fresh"
    assert build_compact_metric_row({"tracked": 2})[0]["value"] == 2
