from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase5v_symbol_workstation_exposes_operational_desk_widgets():
    workstation = (ROOT / "apps/web/src/components/SymbolWorkstation.tsx").read_text(encoding="utf-8")

    assert 'data-phase5v-symbol-desk="true"' in workstation
    assert "SymbolDeskStrip" in workstation
    assert "SourceMiniLedger" in workstation
    assert "EventContextCard" in workstation
    assert "OptionsBridgeSurface" in workstation
    assert "CryptoDerivativesCard" in workstation
    assert "FundProfileCard" in workstation
    assert 'data-phase5v-source-ledger="true"' in workstation
    assert 'data-phase5v-equity-options="true"' in workstation
    assert 'data-phase5v-crypto-derivatives="true"' in workstation


def test_phase5v_asset_route_recomputes_static_catalog_comparison():
    page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")

    assert "withCatalogComparison" in page
    assert "buildCatalogComparisonPoints" in page
    assert "fixture-route-join" in page
    assert "timestamp-inner-join" in page
    assert "Static comparison is useful" in page


def test_phase5v_mobile_and_diagnostics_css_keeps_product_first():
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    assert ".asset-runtime-diagnostics" in css
    assert ".symbol-desk-strip" in css
    assert ".symbol-source-mini-ledger" in css
    assert ".symbol-intelligence-grid.phase5v-context-grid" in css
    assert ".asset-product-shell .product-nav-link.active" in css


def test_phase5v_visual_harness_is_registered():
    package = (ROOT / "apps/web/package.json").read_text(encoding="utf-8")
    script = (ROOT / "apps/web/scripts/capture-phase5v.mjs").read_text(encoding="utf-8")

    assert '"visual:phase5v": "node scripts/capture-phase5v.mjs"' in package
    for marker in [
        "data-phase5v-desk-strip",
        "data-phase5v-source-ledger",
        "data-phase5v-equity-options",
        "data-phase5v-crypto-derivatives",
        "comparisonOverlap > 1",
        "expectNoDerivatives",
    ]:
        assert marker in script
