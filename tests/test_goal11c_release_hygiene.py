from pathlib import Path

from scripts.build_release_zip import iter_release_files


def test_goal11c_release_hygiene_excludes_external_private_and_archives():
    names = [path.relative_to(Path.cwd()).as_posix() for path in iter_release_files()]
    forbidden_tokens = ["external/", "data/private", "data/cache", ".sqlite", ".sqlite3", ".db", "node_modules"]
    assert not any(any(token in name for token in forbidden_tokens) for name in names)
    assert not any(name.startswith(".env.") and name != ".env.example" for name in names)
    assert "pages/23_Research_Tool_Center.py" in names
