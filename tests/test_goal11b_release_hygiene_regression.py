from pathlib import Path
from scripts.build_release_zip import iter_release_files


def test_goal11b_release_excludes_private_external_and_db_files():
    rels = [p.relative_to(Path.cwd()).as_posix() for p in iter_release_files()]
    assert not any(r.startswith("external/") for r in rels)
    assert not any(r.startswith("data/private/") for r in rels)
    assert not any(r.endswith((".db", ".sqlite", ".sqlite3")) for r in rels)
    assert not any("agent-skills-main" in r for r in rels)
    assert ".gitignore" in rels
