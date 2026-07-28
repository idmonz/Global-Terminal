from __future__ import annotations

from scripts import build_release_zip


def test_phase5p_release_includes_replay_product_and_excludes_local_history():
    names = {path.relative_to(build_release_zip.ROOT).as_posix() for path in build_release_zip.iter_release_files()}

    for required in [
        "lib/war_room_map_replay.py",
        "tests/test_phase5p_war_room_map_replay.py",
        "tests/test_phase5p_release_hygiene.py",
        "apps/web/src/components/WarMapReplayWorkspace.tsx",
        "apps/web/scripts/capture-phase5p.mjs",
        "static/api-fixtures/war-room-map-replay.json",
        "docs/PHASE_5P_FINAL_REPORT.md",
        "docs/NEXT_ROADMAP_EXECUTION_PROMPT.md",
    ]:
        assert required in names

    assert ".env" not in names
    assert not any(name.startswith("data/private/") for name in names)
    assert not any(name.endswith((".db", ".sqlite", ".sqlite3")) for name in names)
    assert not any(name.startswith("external (2)/") for name in names)
    assert not any(name.startswith("review_workspace/") for name in names)
    assert not any(name.startswith("apps/web/.next/") for name in names)
    assert not any(name.startswith("apps/web/node_modules/") for name in names)
