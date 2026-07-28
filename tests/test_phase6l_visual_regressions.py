from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _css_rule(css: str, selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", css, re.DOTALL)
    assert match, f"Missing CSS rule: {selector}"
    return match.group("body")


def test_phase6l_watchlist_research_navigation_has_a_readable_desktop_track():
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")
    rule = _css_rule(css, ".watchlist-desk-workspace-grid")
    assert "58px" not in rule
    assert "grid-template-columns: 10.5rem" in rule
    assert ".watchlist-desk-workspace-grid > .product-nav { display: none; }" in css


def test_phase6l_account_sync_ui_is_truthful_accessible_and_action_backed():
    component = (ROOT / "apps/web/src/components/TenantResearchDesk.tsx").read_text(encoding="utf-8")
    for marker in (
        "Research sync",
        "Hosted unavailable",
        "Review sync plan",
        "Explicit sync consent",
        'aria-live="polite"',
        'data-phase6l-sync-state',
        "pending_count",
        "conflict_count",
        "Attention queue",
        'option value="attention"',
    ):
        assert marker in component
    assert "hosted sync successful" not in component.lower()


def test_phase6l_visual_version_capture_is_mechanized_and_registered():
    capture = ROOT / "apps/web/scripts/capture-phase6l.mjs"
    registry = ROOT / "docs/VISUAL_VERSION_REGISTRY.md"
    package = json.loads((ROOT / "apps/web/package.json").read_text(encoding="utf-8"))
    assert capture.exists()
    assert package["scripts"]["visual:phase6l"] == "node scripts/capture-phase6l.mjs"
    registry_text = registry.read_text(encoding="utf-8")
    assert "Phase 6L" in registry_text
    assert "watchlist-desk" in registry_text.lower()
