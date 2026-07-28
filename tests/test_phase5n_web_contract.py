from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase5n_asset_route_defaults_live_and_persists_panel_state():
    page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    routes = (ROOT / "apps/web/src/lib/product-routes.ts").read_text(encoding="utf-8")
    workstation = (ROOT / "apps/web/src/components/SymbolWorkstation.tsx").read_text(encoding="utf-8")

    assert "isAssetRoute" in page
    assert "isAssetRoute || isMapProduct" in page
    for marker in ["chartType", "panels", "compare"]:
        assert marker in routes
        assert marker in workstation
    assert "market_data_as_of" in workstation
    assert "retrieved_at" in workstation
    assert "candlestick" in workstation


def test_phase5n_desktop_asset_shell_allocates_chart_first_width():
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")
    page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")

    assert "asset-product-shell" in page
    assert ".asset-product-shell .product-workspace-grid" in css
    assert "grid-template-columns" in css
    assert ".symbol-analysis-grid" in css

