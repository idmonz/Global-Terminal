from __future__ import annotations

from lib.compliance import contains_forbidden_language
from lib.terminal_ui import (
    data_gap_badge,
    freshness_badge,
    intelligence_card,
    metric_strip,
    mini_bar,
    mini_sparkline,
    severity_badge,
    status_badge,
    terminal_page_header,
    terminal_section_header,
)


def test_terminal_ui_helpers_produce_safe_payloads():
    header = terminal_page_header("Test Terminal", subtitle="Dense neutral dashboard")
    section = terminal_section_header("Radar", caption="Heuristic proxy")
    card = intelligence_card(
        title="Cross-Asset Composite",
        summary="Mixed evidence with explicit data gaps.",
        severity="watch",
        tags=["heuristic", "source status"],
        source="unit test",
        freshness="estimated",
    )
    metrics = metric_strip(metrics=[{"label": "VIX", "value": 18.2, "delta": 1.4, "freshness": "fresh", "sparkline": [1, 2, 1.5]}])

    assert "terminal-shell" in header["html"]
    assert "terminal-section" in section["html"]
    assert "terminal-card" in card["html"]
    assert metrics[0]["label"] == "VIX"
    assert not contains_forbidden_language(card["summary"], allow_disclosure=False)


def test_terminal_badges_and_mini_visuals_render_html():
    assert "Severity" in severity_badge("high")
    assert "Source" in freshness_badge("fresh")
    assert "Data gap" in data_gap_badge()
    assert "terminal-badge" in status_badge("WorldMonitor", "missing")
    assert "terminal-mini-bar" in mini_bar(55, label="Composite")
    assert "<svg" in mini_sparkline([1, 2, 3, 2])
