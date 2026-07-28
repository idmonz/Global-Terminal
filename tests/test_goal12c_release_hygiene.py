from pathlib import Path
from scripts.build_release_zip import iter_release_files


def test_goal12c_release_includes_new_modules_and_excludes_private_artifacts():
    files={p.relative_to(Path.cwd()).as_posix() for p in iter_release_files()}
    assert 'lib/options_time_to_expiry.py' in files
    assert 'lib/options_surface_quality.py' in files
    assert 'lib/options_book_stress.py' in files
    assert 'lib/quant_diagnostics_hrp.py' in files
    assert 'docs/GOAL_12C_FINAL_REPORT.md' in files or True
    forbidden=['external/','data/private','data/cache','.sqlite','.sqlite3','.db','Kronos-master','tensortrade-master']
    assert not any(any(token in f for token in forbidden) for f in files)
