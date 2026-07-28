from __future__ import annotations

import json

from lib.api_contracts import build_api_research_report_payload, validate_api_payload
from lib.research_report_workstation import (
    FORBIDDEN_RESEARCH_PHRASES,
    build_research_report_workstation_contract,
    find_forbidden_report_phrases,
    rewrite_non_advisory_text,
)


def test_research_report_contract_has_required_sections_and_sources():
    payload = build_research_report_workstation_contract()

    assert payload["workspace"] == "research-report"
    assert payload["summary"]["non_advisory"] is True
    assert payload["summary"]["section_count"] >= 8
    assert {section["section_id"] for section in payload["sections"]} >= {
        "executive_summary",
        "market_snapshot",
        "macro_cross_asset_context",
        "news_geopolitical_risk",
        "technical_market_structure",
        "options_gex_volatility_readiness",
        "scenario_matrix",
        "sources_confidence_caveats",
    }
    assert payload["source_register"]
    for section in payload["sections"]:
        assert section["evidence_rows"]
        assert section["not_financial_advice"] is True
        for field in ["source_status", "provider", "confidence", "caveat", "data_gap"]:
            assert field in section


def test_research_report_rewrites_forbidden_advice_language():
    text = "Trade Permission with Recommended Leverage, Long Entry Zone, Stop Loss, Take Profit, Final Action"
    rewritten = rewrite_non_advisory_text(text).lower()

    for phrase in ["trade permission", "recommended leverage", "long entry", "stop loss", "take profit", "final action"]:
        assert phrase not in rewritten


def test_research_report_api_payload_is_json_safe_and_non_advisory():
    payload = build_api_research_report_payload()
    encoded = json.dumps(payload, sort_keys=True).lower()

    valid, issues = validate_api_payload(payload)
    assert valid, issues
    assert payload["payload_type"] == "research_report"
    assert payload["summary"]["forbidden_language_detected"] is False
    assert payload["errors"] == []
    assert find_forbidden_report_phrases(payload["data"]) == []
    for phrase in FORBIDDEN_RESEARCH_PHRASES:
        assert phrase not in encoded
    assert "external (2)" in encoded
    assert "source-bound" in encoded
