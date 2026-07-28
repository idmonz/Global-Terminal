import json
import zipfile
from pathlib import Path

from scripts import build_release_zip


PRIVATE_PATH_MARKERS = (
    "C:\\Users",
    "C:/Users",
    "/mnt/data",
    "/home/",
    "/Users/",
    "sandbox:/",
)


def test_goal12e_release_hygiene_script_excludes_private_external_and_generated_state():
    script = Path("scripts/build_release_zip.py").read_text(encoding="utf-8")
    assert '"external"' in script
    assert '"data/private/"' in script
    assert '"data/cache/"' in script
    assert ".env.example" in script
    assert ".streamlit" in script and "secrets.toml" in script
    assert ".sqlite" in script and ".safetensors" in script
    assert "uploaded_option_chain" in script


def test_goal12e_no_heavy_runtime_dependencies_required():
    req = Path("requirements.txt").read_text(encoding="utf-8").lower()
    for forbidden in ["tensorflow", "torch", "huggingface", "tensortrade", "kronos"]:
        assert forbidden not in req


def test_goal12e_built_release_manifest_and_docs_do_not_leak_private_paths(tmp_path, monkeypatch):
    workspace_manifest = Path(build_release_zip.MANIFEST_NAME)
    original_workspace_manifest = workspace_manifest.read_bytes() if workspace_manifest.exists() else None
    monkeypatch.setattr(build_release_zip, "DIST", tmp_path / "dist")
    monkeypatch.setattr(build_release_zip, "REPORT", tmp_path / "RELEASE_PACKAGE_REPORT.md")

    zip_path, manifest = build_release_zip.build_release()

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        manifest_text = archive.read(build_release_zip.MANIFEST_NAME).decode("utf-8")
        archived_manifest = json.loads(manifest_text)
        leaked_docs = []
        for name in names:
            if not name.startswith("docs/") or not name.endswith((".md", ".json", ".txt")):
                continue
            text = archive.read(name).decode("utf-8")
            if any(marker in text for marker in PRIVATE_PATH_MARKERS):
                leaked_docs.append(name)

    assert manifest["project_root_label"] == "release_root"
    assert archived_manifest["project_root_label"] == "release_root"
    assert archived_manifest["zip_path"] == f"dist/{archived_manifest['zip_name']}"
    assert "project_root" not in archived_manifest
    assert "docs/CODEX_GOAL10B_TO_GOAL12E_REVIEW_PLAN.md" not in names
    assert not any(marker in manifest_text for marker in PRIVATE_PATH_MARKERS)
    assert leaked_docs == []
    if original_workspace_manifest is not None:
        assert workspace_manifest.read_bytes() == original_workspace_manifest
