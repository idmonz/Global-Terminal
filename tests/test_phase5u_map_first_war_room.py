from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_phase5u_war_map_route_uses_compact_source_boundary_before_replay_workspace():
    page = read("apps/web/src/app/page.tsx")
    source_strip = page.index("<MapRuntimeSourceStrip")
    replay_workspace = page.index("<WarMapReplayWorkspace")
    runtime_detail = page.index('className="war-map-runtime-detail"')

    assert source_strip < replay_workspace < runtime_detail
    assert 'data-phase5u-source-strip="true"' in page
    assert "markerCount={markers.length}" in page
    assert "unavailableCount={unavailableSources.length}" in page


def test_phase5u_replay_workspace_renders_map_before_timeline_and_diff():
    replay = read("apps/web/src/components/WarMapReplayWorkspace.tsx")
    toolbar = replay.index("war-map-ops-toolbar")
    map_surface = replay.index("<LeafletWarMap")
    timeline = replay.index("war-map-ops-timeline")
    diff = replay.index("war-map-ops-diff")

    assert 'data-phase5u-map-first="true"' in replay
    assert toolbar < map_surface < timeline < diff
    assert "war-map-ops-compare" in replay
    assert "/api/war-room-map-snapshots" in replay
    assert "/api/war-room-map-replay" in replay


def test_phase5u_css_contains_map_first_density_and_mobile_guards():
    css = read("apps/web/src/app/globals.css")

    for marker in [
        ".global-map-product-header.map-first-header",
        ".war-map-source-strip",
        ".war-map-runtime-detail",
        ".war-map-replay.phase5u-map-first",
        ".war-map-ops-toolbar",
        ".war-map-ops-compare",
        ".war-map-ops-timeline",
        ".war-map-ops-diff",
    ]:
        assert marker in css

    assert "@media (max-width: 620px)" in css
    assert ".war-map-source-strip dl" in css
    assert ".war-map-ops-toolbar .replay-title-block { display: none; }" in css


def test_phase5u_visual_harness_checks_real_viewport_map_position():
    capture = read("apps/web/scripts/capture-phase5u.mjs")
    package = read("apps/web/package.json")

    assert '"visual:phase5u": "node scripts/capture-phase5u.mjs"' in package
    assert "review_workspace" in capture
    assert "phase5u_" in capture
    assert 'data-phase5u-map-first="true"' in capture
    assert "mapTop <= 430" in capture
    assert "mapTop <= 720" in capture
    assert "sourceStrip > 0" in capture
    assert "opsToolbar > 0" in capture
    assert "layerControls > 0" in capture
    assert "eventInspector > 0" in capture
    assert "horizontalOverflow" in capture


def test_phase5y_map_passes_per_event_context_and_compacts_the_map_header():
    page = read("apps/web/src/app/page.tsx")
    map_component = read("apps/web/src/components/LeafletWarMap.tsx")
    replay = read("apps/web/src/components/WarMapReplayWorkspace.tsx")
    css = read("apps/web/src/app/globals.css")

    assert "currentEventContexts={eventContexts}" in page
    assert "defaultSelectedMarkerId={selectedMarkerId}" in page
    assert "contextForMarker(eventContexts, selectedMarker)" in map_component
    assert "selectedContext.marker_id ? asRows(selectedContext.related_news)" in map_component
    assert 'data-event-context-status' in map_component
    assert "window.history.replaceState" in map_component
    assert "useRouter" not in map_component
    assert "Boolean(requestedTime && activeSnapshot.snapshot_id)" in replay
    assert "snapshotReplay={snapshotMode}" in replay
    assert ".map-product-shell .symbol-search" in css
    assert ".global-map-focus-rail" in css
