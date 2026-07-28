from pathlib import Path

from scripts.build_release_zip import EXCLUDED_NAME_TOKENS, iter_release_files


def test_goal11d_release_hygiene_excludes_new_external_references():
    assert {"Kronos-master", "QuantDinger-main", "tensortrade-master", "worldview-main"} <= EXCLUDED_NAME_TOKENS
    names = [path.relative_to(Path.cwd()).as_posix() for path in iter_release_files()]
    forbidden_tokens = ["external/", "data/private", "data/cache", ".sqlite", ".sqlite3", ".db", "node_modules", "Kronos-master", "QuantDinger-main", "tensortrade-master", "worldview-main"]
    assert not any(any(token in name for token in forbidden_tokens) for name in names)
