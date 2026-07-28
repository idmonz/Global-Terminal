from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase6m_attention_is_a_first_class_product_route_and_fixture():
    page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    contracts = (ROOT / "apps/web/src/lib/contracts.ts").read_text(encoding="utf-8")
    fixtures = (ROOT / "apps/web/src/lib/fixtures.ts").read_text(encoding="utf-8")

    assert 'import { AttentionDesk } from "@/components/AttentionDesk"' in page
    assert 'requestedView === "attention-desk"' in page
    assert '<ProductNav active="attention"' in page
    assert 'view=attention-desk' in page
    assert 'key: "attention-desk"' in contracts
    assert 'payloadType: "attention_desk"' in contracts
    assert '"attention-desk": ["items", "all_items", "source_register"]' in fixtures
    assert "origin: firstParam(params?.origin) || firstParam(params?.originView)" in page


def test_phase6m_attention_component_exposes_daily_review_truth_and_controls():
    component = (ROOT / "apps/web/src/components/AttentionDesk.tsx").read_text(encoding="utf-8")

    for marker in (
        'data-phase6m-attention-desk="true"',
        "data-attention-visible-count",
        "data-attention-provider-calls",
        "Since last review",
        "Source truth",
        "Review",
        "Acknowledge",
        "Snooze 4h",
        "Mark review checkpoint",
        "Minimum severity",
        "Source health",
        "No market-provider request",
    ):
        assert marker in component
    assert "localStorage" in component
    assert "aria-live" in component
    assert "router.replace" in component
    assert "originState" in component
    assert "target price" not in component.lower()


def test_phase6m_attention_account_proxy_is_allowlisted_and_bounded():
    proxy = (ROOT / "apps/web/src/app/api/account/[...path]/route.ts").read_text(encoding="utf-8")

    assert '"attention-desk"' in proxy
    assert "attention-desk\\/items\\/" in proxy
    assert '"attention-desk/policy"' in proxy
    assert '"attention-desk/checkpoint"' in proxy
    assert '"attention-desk/audit"' in proxy
    assert "MAX_BODY_BYTES" in proxy
    assert "sameOrigin(request)" in proxy


def test_phase6m_attention_layout_has_stable_desktop_and_390px_tracks():
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    assert ".attention-desk-workspace-grid" in css
    assert "grid-template-columns: 10.5rem minmax(0, 1fr);" in css
    assert "@media (max-width: 720px)" in css
    assert ".attention-queue-row" in css
    assert "overflow-wrap: anywhere" in css
    assert ":focus-visible" in css


def test_phase6m_visual_command_and_capture_harness_are_versioned():
    package = (ROOT / "apps/web/package.json").read_text(encoding="utf-8")
    capture = (ROOT / "apps/web/scripts/capture-phase6m.mjs").read_text(encoding="utf-8")

    assert '"visual:phase6m": "node scripts/capture-phase6m.mjs"' in package
    assert "phase6m_visual" in capture
    assert "attention-daily-review-desktop" in capture
    assert "attention-daily-review-mobile" in capture
    assert "attention-source-degraded" in capture
    assert "attention-no-material-change" in capture
    assert "productNavWidth" in capture
    assert "hiddenRequestCount" in capture
