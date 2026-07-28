from __future__ import annotations

import json
import zipfile

from scripts.build_release_zip import MANIFEST_NAME, build_release, write_report


def test_goal11f_release_count_terms_are_unambiguous():
    zip_path, manifest = build_release()
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        archived_manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
    assert manifest["selected_file_count"] == len(manifest["files"])
    assert archived_manifest["selected_file_count"] == len(archived_manifest["files"])
    assert manifest["expected_zip_entry_count"] == manifest["selected_file_count"] + manifest["manifest_entry_count"]
    assert len(names) == manifest["expected_zip_entry_count"]
    assert MANIFEST_NAME in names


def test_goal11f_release_package_report_uses_explicit_count_language():
    zip_path, manifest = build_release()
    write_report(zip_path, manifest)
    report = zip_path.parents[1] / "docs" / "RELEASE_PACKAGE_REPORT.md"
    text = report.read_text(encoding="utf-8")
    assert "selected_file_count_before_manifest" in text
    assert "expected_zip_entry_count_after_manifest" in text
    assert "actual_zip_entry_count_after_manifest" in text
