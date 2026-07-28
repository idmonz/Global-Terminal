import json
import zipfile
from pathlib import Path

from scripts import build_release_zip


def test_goal13a_release_script_excludes_private_simulations_and_model_artifacts():
    script = Path("scripts/build_release_zip.py").read_text(encoding="utf-8")
    assert '"data/private/actionless_simulations/"' in script
    assert '"actionless_simulations"' in script
    for suffix in [".pt", ".pth", ".ckpt", ".onnx", ".safetensors", ".joblib"]:
        assert suffix in script


def test_goal13a_built_release_contains_goal13a_files_without_private_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(build_release_zip, "DIST", tmp_path / "dist")
    monkeypatch.setattr(build_release_zip, "REPORT", tmp_path / "RELEASE_PACKAGE_REPORT.md")
    zip_path, manifest = build_release_zip.build_release()

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        archived_manifest = json.loads(archive.read(build_release_zip.MANIFEST_NAME).decode("utf-8"))

    assert "lib/actionless_simulation_schema.py" in names
    assert "docs/GOAL_13A_SPEC.md" in names
    assert "tests/test_goal13a_actionless_simulation_schema.py" in names
    assert not any(name == ".env" or name.startswith("data/private/") for name in names)
    assert not any(name.endswith((".pt", ".pth", ".ckpt", ".onnx", ".safetensors", ".joblib")) for name in names)
    assert not any(name in {"external.zip", "external (2).zip"} for name in names)
    assert archived_manifest["project_root_label"] == "release_root"
    assert archived_manifest["zip_path"] == f"dist/{archived_manifest['zip_name']}"
    assert "C:/Users" not in str(archived_manifest)
    assert manifest["actual_zip_entry_count"] == archived_manifest["actual_zip_entry_count"]
