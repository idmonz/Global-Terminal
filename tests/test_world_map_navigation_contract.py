from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_world_map_uses_zoom_adaptive_clusters_and_shareable_region_state():
    source = (ROOT / "apps/web/src/components/LeafletWarMap.tsx").read_text(encoding="utf-8")
    routes = (ROOT / "apps/web/src/lib/product-routes.ts").read_text(encoding="utf-8")

    assert 'from "supercluster"' in source
    assert "MAP_REGION_PRESETS" in source
    assert 'aria-label="Map region presets"' in source
    assert 'params.set("mapRegion"' in source
    assert 'params.set("lat"' in source
    assert 'params.set("lon"' in source
    assert 'params.set("zoom"' in source
    assert 'map.on("zoomend"' in source
    assert 'tileLayer.on("tileerror"' in source
    assert 'data-basemap-state=' in source
    assert '"mapRegion"' in routes
    assert '"lat"' in routes
    assert '"lon"' in routes
    assert '"zoom"' in routes


def test_world_map_prioritizes_active_visible_layers_instead_of_archive_order():
    source = (ROOT / "apps/web/src/components/LeafletWarMap.tsx").read_text(encoding="utf-8")

    assert "priorityLayers(" in source
    assert "priorityLayerRows.map" in source
    assert "layers.slice(0, 12)" not in source


def test_mobile_map_keeps_layers_available_without_covering_the_default_view():
    source = (ROOT / "apps/web/src/components/LeafletWarMap.tsx").read_text(encoding="utf-8")
    styles = (ROOT / "apps/web/src/app/globals.css").read_text(encoding="utf-8")

    assert "layersExpanded" in source
    assert 'aria-expanded={layersExpanded}' in source
    assert 'aria-label={layersExpanded ? "Collapse map layers" : "Expand map layers"}' in source
    assert ".global-map-layer-overlay:not(.expanded) .global-map-layer-row" in styles
    assert ".global-map-canvas:has(.global-map-layer-overlay.expanded) .global-map-focus-rail" in styles
