from __future__ import annotations

import json
from pathlib import Path


def test_phase6n_attention_has_first_viewport_observation_run_controls():
    root = Path(__file__).resolve().parents[1]
    component = (root / "apps/web/src/components/AttentionDesk.tsx").read_text(encoding="utf-8")
    css = (root / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    for marker in (
        'data-phase6n-observation-run="true"',
        "Refresh saved Watchlist",
        "Last completed",
        "Session policy",
        "Provider budget",
        "Cancel run",
        "queued",
        "running",
        "partial",
        "completed",
        "cancelled",
        "failed",
        "/api/account/observation-runs",
    ):
        assert marker in component
    assert "RefreshCw" in component
    assert "Square" in component
    assert ".attention-observation-run" in css
    assert "@media (max-width: 700px)" in css
    assert "min-width: 0" in css


def test_phase6n_fixture_and_contract_are_deterministic_honest_and_bounded():
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / "static/api-fixtures/attention-desk.json").read_text(encoding="utf-8"))
    run = fixture["data"]["observation_run"]

    assert run["provider_call_count"] == 0
    assert run["latest_run"]["status"] in {"completed", "partial", "not-run"}
    assert run["latest_run"]["mode"] == "fixture"
    assert run["refresh_action"]["enabled"] is False
    assert run["refresh_action"]["reason"] == "fixture-does-not-contact-providers"
    assert len(json.dumps(fixture).encode("utf-8")) <= 65_000


def test_phase6n_docs_define_run_clocks_quota_lkg_and_zero_triage_calls():
    root = Path(__file__).resolve().parents[1]
    contract = (root / "docs/PHASE_6N_OBSERVATION_RUN_CONTRACT.md").read_text(encoding="utf-8").lower()

    for marker in (
        "attempted_at",
        "observed_at",
        "retrieved_at",
        "completed_at",
        "last-known-good",
        "alpha vantage",
        "25 requests per day",
        "zero provider calls",
        "queued",
        "cancelled",
        "atomic",
    ):
        assert marker in contract


def test_phase6n_attention_initial_rsc_payload_is_bounded_without_hiding_total_count():
    root = Path(__file__).resolve().parents[1]
    page = (root / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")

    assert "INITIAL_ATTENTION_ROW_LIMIT = 10" in page
    assert ".slice(0, INITIAL_ATTENTION_ROW_LIMIT)" in page
    assert "initial_row_limit" in page
    assert "total_row_count" in page
