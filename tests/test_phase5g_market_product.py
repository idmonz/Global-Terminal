from __future__ import annotations

from pathlib import Path

from scripts import build_release_zip


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_market_home_and_symbol_workstations_use_canonical_url_state():
    page = _read("apps/web/src/app/page.tsx")

    for marker in [
        'view?: string | string[]',
        'symbol?: string | string[]',
        'assetClass?: string | string[]',
        'timeframe?: string | string[]',
        'chartMode?: string | string[]',
        'requestedView === "asset"',
        'function MarketProductHome',
        'ProgressiveSymbolWorkstation',
        'function UnknownSymbolWorkspace',
        'apiBaseUrl="/api/runtime"',
        'data-product-view="market-home"',
        'data-product-view="asset-workspace"',
    ]:
        assert marker in page


def test_product_routes_cover_aapl_btcusdt_refresh_and_unknown_symbol_fallback():
    routes = _read("apps/web/src/lib/product-routes.ts")

    assert 'AAPL' in routes
    assert 'BTCUSDT' in routes
    assert 'view: "asset"' in routes
    assert 'assetClass' in routes
    assert 'timeframe' in routes
    assert "const supported = isRuntimeEligibleSymbol(symbol, assetClass)" in routes
    assert "SAFE_DYNAMIC_SYMBOL" in routes
    assert "invalid-or-unsupported-symbol" in routes


def test_runtime_loader_passes_symbol_context_without_leaking_it_to_other_routes():
    fixtures = _read("apps/web/src/lib/fixtures.ts")

    assert "export interface RuntimeRequestContext" in fixtures
    assert 'url.searchParams.set("symbol"' in fixtures
    assert "requestContext" in fixtures
    assert "SYMBOL_RUNTIME_KEYS" in fixtures


def test_finance_chart_exposes_browser_verifiable_ready_or_fallback_state():
    chart = _read("apps/web/src/components/FinanceChart.tsx")

    assert "data-chart-state={status}" in chart
    assert 'data-chart-points=' in chart
    assert 'data-chart-state="fallback"' in chart


def test_phase5g_product_ui_has_dedicated_dense_responsive_styles():
    css = _read("apps/web/src/app/globals.css")

    for selector in [
        ".product-workspace-grid",
        ".product-nav",
        ".market-product-home",
        ".asset-workspace-header",
        ".timeframe-control",
        ".unknown-symbol-state",
    ]:
        assert selector in css


def test_release_includes_goal_harness_and_repo_skills():
    names = {path.relative_to(build_release_zip.ROOT).as_posix() for path in build_release_zip.iter_release_files()}

    assert "AGENTS.md" in names
    assert "apps/web/AGENTS.md" in names
    for skill_name in [
        "global-terminal-preflight",
        "global-terminal-product-parity",
        "global-terminal-frontend-visual-qa",
        "global-terminal-release-gate",
        "global-terminal-cleanroom-reference",
        "global-terminal-next-goal-writer",
    ]:
        assert f".agents/skills/{skill_name}/SKILL.md" in names
