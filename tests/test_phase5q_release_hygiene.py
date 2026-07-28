from __future__ import annotations

import json
import zipfile

import scripts.build_release_zip as release_zip


def test_phase5q_release_excludes_local_briefs_and_fixture_is_fictional(tmp_path):
    release_zip.DIST = tmp_path
    release_zip.REPORT = tmp_path / "RELEASE_PACKAGE_REPORT.md"
    archive, _manifest = release_zip.build_release()
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        assert "static/api-fixtures/daily-brief.json" in names
        assert not any("research_workspace.db" in name or "daily_brief_captures" in name for name in names)
        fixture = json.loads(zf.read("static/api-fixtures/daily-brief.json"))
    assert fixture["payload_type"] == "daily_brief"
    assert fixture["data"]["historical_truth"] == "fictional-demo"
    assert fixture["data"]["privacy_scope"] == "deterministic-public-fixture"
