from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase5t_options_default_surface_is_visible_analytics_overview():
    component = (ROOT / "apps/web/src/components/OptionsQuantWorkstation.tsx").read_text(encoding="utf-8")
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")
    capture = (ROOT / "apps/web/scripts/capture-phase5t.mjs").read_text(encoding="utf-8")

    assert '"overview"' in component
    assert "OptionsOverviewSurface" in component
    assert 'data-options-analytics-panels="4"' in component
    for marker in ["iv-surface", "greeks-surface", "exposure-surface", "payoff-surface"]:
        assert marker in component
    assert ".options-analytics-grid" in css
    assert "options.optionsPanels < 4" in capture


def test_phase5t_news_route_is_product_workspace_not_generic_contract_viewer():
    page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    css = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")
    capture = (ROOT / "apps/web/scripts/capture-phase5t.mjs").read_text(encoding="utf-8")

    assert 'requestedView === "news"' in page
    assert 'data-product-view="news-workspace"' in page
    assert "NewsIntelligenceProduct" in page
    assert "Story / Event Clusters" in page
    assert "Source-Backed News Workspace" in page
    assert '["fresh", "live/fresh", "cached", "stale"]' in page
    assert ".news-workspace-grid" in css
    assert ".news-workspace-row" in css
    assert ".news-source-rail" in css
    assert "newsStoryRows" in capture
    assert "newsHasStoriesOrHonestGap" in capture
    assert "newsFixture.newsStoryRows < 1" in capture
    assert "options-mobile" in capture
    assert "news-mobile" in capture
