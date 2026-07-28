from lib.data_caveat_explainer import explain_data_caveat
from lib.provider_caveat_panel import build_provider_caveat_panel
from lib.source_freshness_strip import FRESHNESS_LABELS, build_freshness_chip, build_freshness_strip, summarize_source_quality


def test_goal11c_all_freshness_labels_render():
    chips = [build_freshness_chip(label, status=label) for label in FRESHNESS_LABELS]
    statuses = {chip["status"] for chip in chips}
    assert set(FRESHNESS_LABELS) <= statuses
    assert explain_data_caveat("historical-only")["explanation"]
    assert explain_data_caveat("missing-key")["explanation"]
    summary = summarize_source_quality(chips)
    assert summary["counts"]["missing-key"] == 1


def test_goal11c_provider_caveat_panel_missing_key_explicit():
    panel = build_provider_caveat_panel([{"provider_id": "eia", "requires_key": True, "is_configured": False}])
    assert panel["chips"][0]["status"] == "missing-key"
    assert build_freshness_strip([])["chips"][0]["status"] == "unavailable"
