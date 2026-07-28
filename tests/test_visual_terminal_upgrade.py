from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from lib.compliance import contains_forbidden_language
from lib.data_status import success
from lib.fundamentals import build_financial_visual_panels
from lib.intelligence_cards import build_ai_brief_card, build_data_gap_cards, build_market_intelligence_cards
from lib.map_viz import (
    build_chokepoint_risk_map,
    build_event_timeline_chart,
    build_news_severity_bar,
    build_source_freshness_chart,
    build_terminal_event_map,
)
from lib.options_flow import build_options_visual_payload
from lib.screeners import build_screener_visual_summary


ROOT = Path(__file__).resolve().parents[1]


def test_map_and_chart_builders_return_figures_or_graceful_fallbacks():
    news = pd.DataFrame(
        [
            {
                "title": "Hormuz tanker disruption",
                "severity": "high",
                "lat": 26.5667,
                "lon": 56.25,
                "source": "test",
                "freshness": "fresh",
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    event_fig, event_frame, event_status = build_terminal_event_map(news)
    choke_fig, choke_frame, choke_status = build_chokepoint_risk_map(news_items=news)
    timeline_fig, _, timeline_status = build_event_timeline_chart(pd.DataFrame([{"period": datetime.now(timezone.utc), "total_count": 1, "high_count": 1}]))
    severity_fig, _, severity_status = build_news_severity_bar(news)
    freshness_fig, _, freshness_status = build_source_freshness_chart([success({}, source="unit", provider="pytest")])

    assert event_fig is not None and event_status.ok and not event_frame.empty
    assert choke_fig is not None and choke_status.ok and len(choke_frame) >= 8
    assert timeline_fig is not None and timeline_status.ok
    assert severity_fig is not None and severity_status.ok
    assert freshness_fig is not None and freshness_status.ok


def test_terminal_event_map_coordinate_gap_is_soft_fallback():
    event_fig, event_frame, event_status = build_terminal_event_map(pd.DataFrame([{"title": "No coordinate event"}]))
    assert event_fig is None
    assert event_status.ok
    assert event_status.is_estimated
    assert "fallback" in event_status.warning.lower()


def test_visual_payload_builders_and_cards_are_safe():
    financial = build_financial_visual_panels({"ticker": "AAPL", "availability": {"income": True}, "ratios": {"trailing_pe": 22}, "balance_quality": {"debt_to_assets": 0.2}, "data_gaps": []})
    options = build_options_visual_payload({"ticker": "AAPL", "put_call_oi_ratio": 0.8, "max_pain_proxy": {"max_pain_strike": 200}})
    screener = build_screener_visual_summary(pd.DataFrame([{"ticker": "AAPL", "return_1m_pct": 4.0, "realized_volatility_pct": 22.0, "data_status": "fresh"}]))
    cards = build_market_intelligence_cards({"equity": {"above_50dma_pct": 55}, "risk": {"vix": 18}})
    cards.extend(build_data_gap_cards(["Optional provider unavailable."]))
    cards.append(build_ai_brief_card(context={"provider": "rule_based", "model": "deterministic-neutral-fallback"}))

    assert financial["metric_cards"]
    assert options["summary_cards"]
    assert screener["result_cards"]
    assert all(not contains_forbidden_language(card.get("summary", ""), allow_disclosure=False) for card in cards)


def test_release_hygiene_patterns_and_runtime_worldmonitor_boundary():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in ["**/__pycache__/", ".pytest_cache/", "*.pyc", "data/cache/", "external/", ".streamlit/secrets.toml"]:
        assert pattern in gitignore

    runtime_files = list((ROOT / "lib").glob("*.py")) + list((ROOT / "pages").glob("*.py")) + [ROOT / "app.py"]
    for path in runtime_files:
        text = path.read_text(encoding="utf-8")
        assert "external.worldmonitor" not in text
        assert "worldmonitor-main" not in text
        for line in text.splitlines():
            lowered = line.lower()
            if "live ais" in lowered or "live vessel" in lowered:
                assert any(token in lowered for token in ["no live", "not claim", "not claimed", "unavailable"])
