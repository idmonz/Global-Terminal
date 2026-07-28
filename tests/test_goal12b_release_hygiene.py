from pathlib import Path
from scripts.build_release_zip import iter_release_files


def test_goal12b_release_includes_new_modules_and_excludes_uploads_external():
    files={p.relative_to(Path.cwd()).as_posix() for p in iter_release_files()}
    assert ".env.example" in files
    assert "lib/options_chain_ingestion.py" in files
    assert "lib/options_vol_surface.py" in files
    assert "lib/options_book_risk.py" in files
    assert "lib/quant_diagnostics_report.py" in files
    assert not any(f.startswith("external/") for f in files)
    assert not any(f.endswith(".csv") and not f.startswith("static/index_constituents/") for f in files if "tests/fixtures" not in f)
    assert not any("agent-skills" in f or "Kronos" in f or "tensortrade" in f for f in files)
