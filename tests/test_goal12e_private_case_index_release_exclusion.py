from pathlib import Path


def test_goal12e_release_hygiene_excludes_private_case_index_and_review_queue():
    script = Path("scripts/build_release_zip.py").read_text(encoding="utf-8")
    assert '"data/private/"' in script
    assert "external" in script
    assert "case_index.json" not in Path(".").glob("*")


def test_goal12e_private_artifact_names_not_packaged_if_release_exists():
    zip_path = Path("global_market_terminal_release.zip")
    if not zip_path.exists():
        return
    import zipfile
    names = zipfile.ZipFile(zip_path).namelist()
    assert all(not name.startswith("data/private/") for name in names)
    assert all("case_index.json" not in name for name in names)
    assert all("surface_review_queue.json" not in name for name in names)
