from pathlib import Path


def test_phase6o_alert_manager_is_a_product_surface_not_contract_diagnostics():
    root = Path(__file__).resolve().parents[1]
    component = (root / "apps/web/src/components/WatchlistAlertManager.tsx").read_text(encoding="utf-8")
    page = (root / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    css = (root / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    for marker in (
        'data-phase6o-alert-manager="true"',
        "Watchlist Alert Manager",
        "Create rule",
        "Run due checks",
        "Trigger history",
        "Source & clocks",
        "Worker stopped",
        "No rules yet",
        "/api/account/alert-manager/rules",
        "/api/account/alert-manager/evaluations",
        "X-CSRF-Token",
        'aria-live="polite"',
        'data-active-tab={tab}',
        "price_above",
        "price_below",
        "absolute_percent_move",
        "material_saved_change",
        "source_degradation",
        "loadManager(false)",
    ):
        assert marker in component
    assert 'requestedView === "alert-manager"' in page
    assert 'active="alerts"' in page
    assert ".alert-manager-layout" in css
    assert ".alert-manager button:focus-visible" in css
    assert "@media (max-width: 700px)" in css
    assert '.alert-manager[data-active-tab="rules"] .alert-rule-builder' in css
    assert "API Contract Payload Preview" not in component


def test_phase6o_alert_manager_has_exact_evidence_and_return_state():
    root = Path(__file__).resolve().parents[1]
    component = (root / "apps/web/src/components/WatchlistAlertManager.tsx").read_text(encoding="utf-8")
    analyst = (root / "apps/web/src/components/AnalystWorkspace.tsx").read_text(encoding="utf-8")

    for marker in ("Analyst", "News", "Brief", "Map", "originState", "selectedTrigger"):
        assert marker in component
    assert 'url.searchParams.set("mode", targetMode)' in component
    assert 'runtimeMode === "fixture" ? "fixture" : "cache"' in component
    assert 'text(state.origin, "") === "alert-manager"' in analyst
    assert "Return to Alert Manager" in analyst


def test_phase6o_fixture_exposes_required_failure_and_truth_states():
    import json

    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "static/api-fixtures/watchlist-alert-manager.json").read_text(encoding="utf-8"))
    data = payload["data"]

    assert data["contract_version"] == "watchlist_alert_manager.v1"
    assert data["summary"]["provider_call_count"] == 0
    assert data["worker"]["view_starts_worker"] is False
    assert data["hosted_readiness"]["status"] == "unavailable"
    assert data["delivery_channels"]["in_app"] == "available"
    assert data["delivery_channels"]["email"] == "unavailable"
    assert {"paused", "expired", "cancelled", "quota-blocked", "worker-offline", "conflict"} <= set(data["state_catalog"])
    assert data["triggers"][0]["live_intelligence_claimed"] is False


def test_phase6o_visual_handoff_covers_product_acceptance_matrix():
    root = Path(__file__).resolve().parents[1]
    capture = (root / "apps/web/scripts/capture-phase6o.mjs").read_text(encoding="utf-8")
    verify = (root / "apps/web/scripts/verify-phase6o-visual-summary.mjs").read_text(encoding="utf-8")
    handoff = (root / "scripts/run_phase6o_visual_handoff.ps1").read_text(encoding="utf-8")

    for marker in (
        "phase6o.visual.v1",
        "alert-manager-create-empty-desktop",
        "alert-manager-active-rule-desktop",
        "alert-manager-trigger-history-desktop",
        "alert-manager-mobile-390x844",
        "alert-manager-version-conflict",
        "alert-manager-account-b-isolated",
        "alert-manager-drilldown-${label.toLowerCase()}",
        "providerRequestCount",
        "inspectFocusVisible",
        "initial HTML",
    ):
        assert marker in capture
    assert "100_000" in capture
    assert "Account A/B visual isolation is not proved" in verify
    assert "visual:verify:phase6o" in handoff
