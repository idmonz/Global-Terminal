from pathlib import Path

from scripts.build_release_zip import iter_release_files


def test_goal12a_release_includes_required_files_and_excludes_external():
    files = {p.relative_to(Path.cwd()).as_posix() for p in iter_release_files()}
    assert ".env.example" in files
    assert "pages/24_Options_Quant_Model_Lab.py" in files
    assert "lib/options_pricing_models.py" in files
    assert not any(f.startswith("external/") for f in files)
    assert not any("Kronos" in f or "optlib" in f or "tensortrade" in f for f in files)
